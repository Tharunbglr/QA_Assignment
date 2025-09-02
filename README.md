
# QA_Assignment

## Overview

This repository contains the QA assignment deliverables for testing the Segwise.ai dashboard. It includes:

- QA Report documenting identified issues and insights
- Python Selenium automation script for basic dashboard testing
- This README file with setup and execution instructions

## Repository Structure

```
segwise-qa-assignment/
├── QA_Report.md                       
├── requirements.txt
├── test_dashboard.py                  
├── README.md                         
```

## Requirements

- Python 3.8 or higher
- Google Chrome browser (latest version)
- ChromeDriver (compatible with your Chrome version) added to system PATH

## Setup Instructions

1. Clone the repository:

   ```
   git clone <repository-url>
   cd qa_assignment
   ```

2. Install required Python packages:

   ```
   pip install selenium pytest
   ```

3. Ensure ChromeDriver is installed and accessible from the command line.

## Running the Automation Script

Run the script from the project directory:

```
python test_dashboard.py
```

Or run with pytest to see detailed output:

```
pytest test_dashboard.py -v
```

## What the Script Does

- Opens the Segwise login page
- Logs in with the test credentials (qa@segwise.ai / segwise_test)
- Navigates to the dashboard
- Checks for presence of a key metric ("Cost Per Install")

## Expected Output

You should see console messages indicating success or failure of each step, for example:

```
All tests completed successfully!
```




