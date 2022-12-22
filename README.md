# SauceDemoTAF
Test Request for a Company

## Please Be Sure you have installed: 
Python
pip
Behave
Selenium
Allure-behave
allure-commandline

## User Guide of Behave Framework:

You can find information about behave framework here: https://behave.readthedocs.io/en/latest/ You can find information more information about command line here: https://docs.python.org/3/using/cmdline.html

You can find information more information about command line here: https://docs.python.org/3/using/cmdline.html

## How to Run test cases

On the Project Path run (commnad Line):
behave .\Features\


## How To run Reports:
On the Project Path run (commnad Line):
npm install -g allure-commandline --savedev     

## Create Reports
behave -f allure_behave.formatter:AllureFormatter -o reports/ features
Open reports HTML and run Server
allure serve reports/
