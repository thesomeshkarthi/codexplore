import os
import re
import sys
from optparse import OptionParser
import banfunc
import webbrowser
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED, ALL_COMPLETED
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
DEFAULT_NUM_WORKERS = 7

def exclusionlist():
    xlist = []
    xpath = os.path.join(origin, "excluded.txt")
    if not os.path.exists(xpath):
        pass
    else:
        with open(os.path.join(origin, "excluded.txt"), 'r') as excldfile:
            for x_item in excldfile:
                x_item = os.path.normpath(os.path.join(origin, x_item))
                xlist.append(x_item.rstrip())
    return xlist

# This below function is used for extracting the repeating comment segments from a line of C++ code 
def stripmulticomments(syntx):
    if((syntx.find("/*")>=0) and (syntx.find("*/")>=0) and (syntx.find("*/")>syntx.find("/*"))):
        syntx = syntx[:syntx.find("/*")] + syntx[syntx.find("*/")+2:]
        return stripmulticomments(syntx)
    else:
        return syntx  

def fileSearch(dirpath):
    global max_futures
    global futures
    global executor
    global kwlist
    global fileslst

    xlist = exclusionlist()

    try:
        dircontents = os.listdir(dirpath)
    except:
        print ("Directory path not accessible. Please use a valid command!")
        os._exit(0)
    for filename in dircontents:
        filepath = os.path.normpath(os.path.join(dirpath, filename))
        if (os.path.isdir(filepath)):
            if filepath in xlist:
                pass
            else:
                fileSearch(filepath)
        elif (re.search(r'\b'+extn_c+r'\b', filename) or re.search(r'\b'+extn_h+r'\b', filename) or re.search(r'\b'+extn_cc+r'\b', filename)or re.search(r'\b'+extn_cpp+r'\b', filename)):
            # See if we need to free up some futures before submitting another job.
            if len(futures) >= max_futures:
                done_futures, remaining_futures = wait(futures, return_when=FIRST_COMPLETED)
                futures = list(remaining_futures)
                consumeResults(done_futures)
            future = executor.submit(searchFile, filepath, badfuncs)
            futures.append(future)

    return

def searchFile(filepath, badfuncs):
    res_kwlist = []
    res_fileslst = []
    res_line_count_lst = []
    res_value_lst = []

    print(filepath)

    file_lines = []
    successful_read = False
    possible_encodings = ['utf8', 'windows-1252', 'UTF-16LE']  # Some files in some driver components are encoded with different formats
    for enc in possible_encodings:
        try:
            if enc != 'utf8':
                print(f"Trying again with {enc}...")
            with open(filepath, 'r', encoding=enc) as in_file:
                file_lines = in_file.read().splitlines()
                successful_read = True
            break
        except Exception:
            print(f"WARNING: Unable to open {filepath} with {enc}.")
    if not successful_read:
        print(f"ERROR: Unable to open {filepath}.")
        sys.exit(1)

    for i in range(len(badfuncs)):
        for key,value in badfuncs[i].items():
            for keyword in key:
                block_comment_flag = 0
                initial_flag = 0
                line_count = 0
                for line in file_lines:
                    line_count += 1
                    #(BEGIN) Extracting the valid code segments from the code written along with the comments
                    if (line.lstrip().startswith("/*") and (initial_flag == 0)):
                        block_comment_flag = 1
                        initial_flag = 1
                    if ((line.find("*/") >= 0) and (block_comment_flag == 1) and (initial_flag == 1)):
                        block_comment_flag = 0
                        initial_flag = 0
                        line = line[line.find("*/")+2:]
                    if ((block_comment_flag == 1) and (initial_flag == 1)):
                        pass
                    elif (not line.lstrip().startswith("//")):
                        if ((line.find("/*")>0) and (line.find("*/")<0)):
                            block_comment_flag = 1
                            initial_flag = 1
                            line = line[:line.find("/*")+1]
                        elif ((line.find("/*")>=0) and (line.find("*/")>=0) and (line.find("*/")>line.find("/*"))):
                            line = line[:line.find("/*")] + line[line.find("*/")+2:]
                            line = stripmulticomments(line)
                        if (line.find("//")):
                            line = line[:line.find("//")]
                            #(END) Extracting the valid code segments from the code written along with the comments
                            # Searching the banned function keyword from a legitimate code segment
                        if re.search(r'\b'+keyword+r'\b', line):
                            res_kwlist.append(keyword)
                            res_fileslst.append(filepath)
                            res_line_count_lst.append(str(line_count))
                            res_value_lst.append(value)
        
    return res_kwlist, res_fileslst, res_line_count_lst, res_value_lst

def consumeResults(done_futures):
    global kwlist
    global fileslst
    global _row

    for done_future in done_futures:
        res_kwlist, res_fileslst, res_line_count_lst, res_value_lst = done_future.result()
        for i in range(len(res_kwlist)):  # all result lists will be the same length
            _row += 1
            _color = row_color[(_row + 1) % 2]
            html_file.write("<tr bgcolor=" + _color + ">" + "<td>" + str(_row) + "</td>" + "<td>" + "'" + res_kwlist[i] + "'" + "</td>" + "<td>" + res_fileslst[i] + ': ' + res_line_count_lst[i] + '</td>' + '<td>' + res_value_lst[i] + '</td></tr>')
        kwlist.extend(res_kwlist)
        fileslst.extend(res_fileslst)

def bfstats(lst):
    if (len(lst) == 0):
        print("No banned functions found")
    else:
        item_counts = Counter(lst)
        unique_items_sorted = [item for item, count in item_counts.most_common()]
        for item in unique_items_sorted:
            html_file.write(f"{item}: {lst.count(item)}" + "<br>")
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    kwlist = []
    fileslst = []
    badfuncs = banfunc.banfunc()    # Loading the list of the dictionaries that contain C++ band functions

    # File types that'll be searched
    extn_c = '\.c'
    extn_h = '\.h'
    extn_cpp = '\.cpp'
    extn_cc = '\.cc'

    parser = OptionParser()
    parser.add_option("-f", "--filename", dest="dirpath", help="C++ code directory location", metavar="FILE")
    parser.add_option("-j", "--jobs", dest="num_jobs", help="Number of worker processes to be created. Defuault is 8")
    (options, args) = parser.parse_args()
    if (len(sys.argv) > 1) and (sys.argv[1]=="-f" or sys.argv[1].startswith("--filename")):
        origin = options.dirpath
    else:
        print ("Invalid parameter(s). Use: python .\codeexplore.py -f <C/C++ directory path>")
        sys.exit(1)
    if options.num_jobs:
        try:
            options.num_jobs = int(options.num_jobs)
        except:
            print("Invalid argument for -j/--jobs. Value must be an integer")
            sys.exit(1)

    print("Search path root:", origin)

    # Initializing the colors for the table rows
    _row = 0
    row_color = ["\'#F2F3F4\'","\'#E5E7E9\'"]

    # Designing the html page for generating the report
    html_file = open('banned_functions.html', 'w+')
    html_file.write('<table style=\"width:100%\">')
    html_file.write('<style type="text/css">'
                    +'.tg  {border-collapse:collapse;border-spacing:0;}'
                    +'.tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;}'
                    +'.tg th{font-family:Arial, sans-serif;font-size:14px;font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;}'
                    +'.tg .tg-yw4l{vertical-align:top}'
                    +'</style>'
                    +'<table class="tg">')
    html_file.write('<p><font face="Arial"><h3>Banned Functions in C/C++ Code</h3></font></p>')
    html_file.write('<tr class="tg-yw4l">' + '<th> <h3>Index</h3> </th>' + '<th> <h3>Keyword</h3> </th>' + '<th> <h3>Found in<h3> </th>' + '<th> <h3>Suggestion</h3> </th>' + '</tr>')
    
    num_workers = DEFAULT_NUM_WORKERS
    if options.num_jobs:
        num_workers = options.num_jobs - 1  # reserve one job for the parent/producer process
    max_futures = num_workers * 2  # We define a max number of pending jobs to limit memory usage
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        print("Searching...")
        fileSearch(origin)
        # Wait for all remaining futures to complete
        if len(futures) > 0:
            done_futures, remaining_futures = wait(futures, return_when=ALL_COMPLETED)
            consumeResults(done_futures)
    
    html_file.write(f"<mark>{str(_row)}</mark> instances found in the repository, <mark>{origin}</mark>"+"<br>")
    html_file.write('<br> Frequencies of the banned functions found in the code: <br>')
    bfstats(kwlist)
    html_file.write('<br> Frequencies of the files containing the banned functions: <br>')
    bfstats(fileslst)
    html_file.write('<br>')
    # In case there's no banned function in the code ...             
    if (_row == 0):
        html_file.write('<p><font face="Arial"><h3>Awesome! There\'s none in here :) </h3></font></p>')
    html_file.close()

    webbrowser.open('banned_functions.html')
    print ("Done!!!")
    os._exit(0) # Exit without a prompt
    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#