# Reads and checks perf/config.toml (Python's built-in tomllib, no extra package).
#
# Used by perf/run.py (which profile, how to start the app) and by perf/locustfile.py (the scenarios and the
# load shape). Every mistake in the file is reported with its place, before the app is started.

import os
import tomllib

PERF_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PERF_DIR)
DEFAULT_CONFIG = os.path.join(PERF_DIR, 'config.toml')

SCENARIOS = ('browse', 'cart', 'buy')

# Every endpoint the scenarios call, as "METHOD name": the rows of the results table (in this order) and the
# names the thresholds of the config may use. The declined card has its own row: its 402 is expected.
ENDPOINTS = (
    'POST /auth/login',
    'GET /products',
    'GET /products/{id}',
    'POST /cart/items',
    'GET /cart/items',
    'DELETE /cart/items/{id}',
    'DELETE /cart/items',
    'POST /orders',
    'POST /orders (declined card)',
    'GET /orders/{id}',
    'POST /auth/logout',
)

# What a threshold can limit (all "at most"): response time percentiles in ms and the share of errors in %
METRICS = ('p50_ms', 'p95_ms', 'p99_ms', 'error_pct')
THRESHOLD_SCOPES = ('total', 'each_endpoint', 'endpoints')


class ConfigError(Exception):
    """perf/config.toml (or the file given with --config) has a mistake."""


def _number(value, where, minimum=0, integer=False, allow_equal=True):
    kind = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, kind):
        raise ConfigError(f'{where} must be {"a whole number" if integer else "a number"}, not {value!r}')
    if value < minimum or (value == minimum and not allow_equal):
        raise ConfigError(f'{where} must be {">=" if allow_equal else ">"} {minimum}, not {value!r}')
    return value


def _range(value, where, integer=False):
    if not (isinstance(value, list) and len(value) == 2):
        raise ConfigError(f'{where} must be [min, max], not {value!r}')
    low = _number(value[0], f'{where}[0]', integer=integer)
    high = _number(value[1], f'{where}[1]', integer=integer)
    if low > high:
        raise ConfigError(f'{where}: min {low} is bigger than max {high}')
    return low, high


def _section(config, name, where=''):
    value = config.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f'missing section [{where}{name}]')
    return value


def load(path=None):
    """The checked settings as a dict. Raises ConfigError with a readable message."""
    path = path or DEFAULT_CONFIG
    try:
        with open(path, 'rb') as file:
            config = tomllib.load(file)
    except FileNotFoundError:
        raise ConfigError(f'config file not found: {path}')
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f'{path} is not valid TOML: {error}')

    run = _section(config, 'run')
    for key in ('stop_timeout', 'app_start_timeout', 'progress_every', 'token_renew_margin'):
        _number(run.get(key), f'[run] {key}')
    _number(run.get('request_timeout'), '[run] request_timeout', allow_equal=False)
    _number(run.get('token_ttl_seconds'), '[run] token_ttl_seconds', minimum=1, integer=True)
    if run['token_renew_margin'] >= run['token_ttl_seconds']:
        raise ConfigError('[run] token_renew_margin must be smaller than token_ttl_seconds')

    accounts = _section(config, 'accounts')
    if not (isinstance(accounts.get('usernames'), list) and accounts['usernames']
            and all(isinstance(name, str) and name for name in accounts['usernames'])):
        raise ConfigError('[accounts] usernames must be a list of user names')
    if not isinstance(accounts.get('password'), str):
        raise ConfigError('[accounts] password must be text')

    checkout = _section(config, 'checkout')
    for key in ('first_name', 'last_name', 'postal_code', 'card', 'declined_card'):
        if not (isinstance(checkout.get(key), str) and checkout[key]):
            raise ConfigError(f'[checkout] {key} must be non-empty text')
    _number(checkout.get('declined_card_every'), '[checkout] declined_card_every', integer=True)
    _number(checkout.get('tax_rate'), '[checkout] tax_rate')

    scenarios = _section(config, 'scenarios')
    unknown = set(scenarios) - set(SCENARIOS)
    if unknown:
        raise ConfigError(f'unknown scenario(s) {sorted(unknown)}; the scenarios are {list(SCENARIOS)}')
    for name in SCENARIOS:
        scenario = _section(scenarios, name, 'scenarios.')
        _number(scenario.get('weight'), f'[scenarios.{name}] weight', integer=True)
        _range(scenario.get('wait'), f'[scenarios.{name}] wait')
    _range(scenarios['browse'].get('products_opened'), '[scenarios.browse] products_opened', integer=True)
    for name in ('cart', 'buy'):
        low, _ = _range(scenarios[name].get('items'), f'[scenarios.{name}] items', integer=True)
        if low < 1:
            raise ConfigError(f'[scenarios.{name}] items: a flow needs at least 1 product')
    if not any(scenarios[name]['weight'] for name in SCENARIOS):
        raise ConfigError('at least one scenario needs a weight above 0')

    profiles = _section(config, 'profiles')
    if not profiles:
        raise ConfigError('[profiles] is empty')
    for name, profile in profiles.items():
        where = f'[profiles.{name}]'
        if not isinstance(profile, dict):
            raise ConfigError(f'{where} must be a table')
        if not isinstance(profile.get('description', ''), str):
            raise ConfigError(f'{where} description must be text')
        stages = profile.get('stages')
        if not (isinstance(stages, list) and stages):
            raise ConfigError(f'{where} needs stages = [{{ duration = ..., users = ..., spawn_rate = ... }}, ...]')
        for number, stage in enumerate(stages, 1):
            at = f'{where} stage {number}'
            if not isinstance(stage, dict) or set(stage) != {'duration', 'users', 'spawn_rate'}:
                raise ConfigError(f'{at} must have exactly duration, users and spawn_rate')
            _number(stage['duration'], f'{at} duration', allow_equal=False)
            _number(stage['users'], f'{at} users', integer=True)
            _number(stage['spawn_rate'], f'{at} spawn_rate', allow_equal=False)
        profile['thresholds'] = _thresholds(profile.get('thresholds'), f'{where[:-1]}.thresholds]')
    config['path'] = os.path.abspath(path)
    return config


def _limits(value, where):
    if not isinstance(value, dict) or not value:
        raise ConfigError(f'{where} must be a table of limits, e.g. {{ p95_ms = 200, error_pct = 0 }}')
    for metric, limit in value.items():
        if metric not in METRICS:
            raise ConfigError(f'{where}: unknown limit {metric!r}; the limits are {", ".join(METRICS)}')
        _number(limit, f'{where} {metric}')
    return dict(value)


def _thresholds(value, where):
    """The thresholds of a profile: total and error_pct are required, so real errors can always fail a run."""
    if not isinstance(value, dict):
        raise ConfigError(f'{where} is missing: every profile needs at least total = {{ error_pct = ... }}')
    unknown = set(value) - set(THRESHOLD_SCOPES)
    if unknown:
        raise ConfigError(f'{where}: unknown key(s) {sorted(unknown)}; use {", ".join(THRESHOLD_SCOPES)}')
    thresholds = {'total': _limits(value.get('total'), f'{where} total'),
                  'each_endpoint': _limits(value['each_endpoint'], f'{where} each_endpoint')
                  if 'each_endpoint' in value else {},
                  'endpoints': {}}
    if 'error_pct' not in thresholds['total']:
        raise ConfigError(f'{where} total needs error_pct, so real errors always count')
    endpoints = value.get('endpoints', {})
    if not isinstance(endpoints, dict):
        raise ConfigError(f'{where} endpoints must be a table: "POST /orders" = {{ p95_ms = ... }}')
    for endpoint, limits in endpoints.items():
        if endpoint not in ENDPOINTS:
            raise ConfigError(f'{where} endpoints: unknown endpoint {endpoint!r}; the endpoints are: '
                              f'{", ".join(ENDPOINTS)}')
        thresholds['endpoints'][endpoint] = _limits(limits, f'{where} endpoints."{endpoint}"')
    return thresholds


def apply_overrides(thresholds, overrides):
    """Thresholds with the --threshold options of the command line on top. Each option is
    [scope:]metric=value, scope = total (the default), each_endpoint or an endpoint ("POST /orders")."""
    result = {'total': dict(thresholds['total']), 'each_endpoint': dict(thresholds['each_endpoint']),
              'endpoints': {name: dict(limits) for name, limits in thresholds['endpoints'].items()}}
    for option in overrides or ():
        scope, _, assignment = option.rpartition(':') if ':' in option else ('total', '', option)
        metric, equals, raw = assignment.partition('=')
        scope, metric = scope.strip(), metric.strip()
        if not equals or metric not in METRICS:
            raise ConfigError(f'--threshold {option!r}: write [scope:]metric=value, metric one of '
                              f'{", ".join(METRICS)}, e.g. --threshold p95_ms=1')
        try:
            limit = float(raw)
        except ValueError:
            raise ConfigError(f'--threshold {option!r}: {raw!r} is not a number')
        if limit < 0:
            raise ConfigError(f'--threshold {option!r}: a limit cannot be negative')
        if scope in ('total', 'each_endpoint'):
            result[scope][metric] = limit
        elif scope in ENDPOINTS:
            result['endpoints'].setdefault(scope, {})[metric] = limit
        else:
            raise ConfigError(f'--threshold {option!r}: unknown scope {scope!r}; use total, each_endpoint or '
                              f'one of: {", ".join(ENDPOINTS)}')
    return result


def profile(config, name):
    """The profile called name, or ConfigError listing the ones that exist."""
    if name not in config['profiles']:
        raise ConfigError(f'unknown profile {name!r}; the profiles are: {", ".join(config["profiles"])}')
    return config['profiles'][name]


def total_duration(profile_settings):
    return sum(stage['duration'] for stage in profile_settings['stages'])


def peak_users(profile_settings):
    return max(stage['users'] for stage in profile_settings['stages'])
