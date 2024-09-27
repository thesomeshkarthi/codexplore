# codexplore
Code Scanning Tool to Identify depreciated C/C++ Functions in a Repository

This tool is used to spot the usage of any C++ banned functions in a code repository. The identified C++ banned functions are displayed in a tabular form along with their locations in the code and their secure alternatives. An HTML page is displayed once the search is complete.

The code parses https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/28719-banned-api-usage-use-updated-function-replacement to determine all of the depreciated functions published by Microsoft.

Usage>> python codexplore.py -f <C/C++ directory path> [-j <number of worker processes]
