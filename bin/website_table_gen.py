#!/usr/bin/env python
#
# Programme that converts a derived frequency plan CSV into a format suitable
# for the CARES website.
#
# The input file to this programme is the 2m/70cm CSV that has been generated
# directly from the Excel format ICS-217A frequency plan.
#
# Time-stamp: <2023-02-06 15:51:05 acw> @author: Andrew Watson
# 
# This work is licensed under a CC BY-NC-SA 4.0 international license. 
#

import csv
from enum import IntEnum
import getopt
import sys

# ----------------------------------------------------------------------
# Constants - all should be capitalised
# ----------------------------------------------------------------------

# Be sure to update this string as it is prepended to the list of rows and
# added to the end of the list for writing out to the CSV.
CARES_SENTINEL_ROW = ",YELLOW,147.120000,+,0.600000,Tone,100.0,100.0,023,NN,FM,5.00,,,,,,,,"

# This can be changed if a tone value is required. Otherwise, it's set to blank
# for any channels that are not using either CTCSS tone, DCS tone or tone
# squelch.
DEFAULT_CTCSS_TONE = ''

DEFAULT_TONE_MODE = '' # There is no mode - neither Tone, TSQL, DCS etc.
BASIC_TONE_MODE   = 'Tone'
TONE_SQUELCH_MODE = 'TSQL'
DCS_TONE_MODE = 'DTCS' # CHIRP uses DTCS for this field.

# DCS is the more common moniker for digital coded squelch.
WEB_DCS_TONE_MODE_ACRONYM = 'DCS'

# The programme can be set to skip reading up to the first nine rows. However,
# this is the default number it will skip.
DEFAULT_NUM_ROWS_TO_SKIP = 0

# The CHIRP CSV that was generated from the ICS 217A Excel spreadsheet has these
# column headings in this order.

class CHIRP_CSV_COLUMNS(IntEnum):
    CHANNEL_NUM = 0   
    CHANNEL_NAME = 1
    FREQUENCY = 2
    DUPLEX = 3
    OFFSET = 4
    TONE_MODE = 5
    TX_TONE = 6
    RX_TONE = 7
    DTCS_CODE = 8
    DTCS_POLARITY = 9
    MODE = 10
    TSTEP = 11
    SKIP = 12
    COMMENT = 13
    URCALL = 14
    RPT1CALL = 15
    RPT2CALL = 16
    
# The columns used by the CARES web site's input CSV

class WEBSITE_CSV_COLUMNS(IntEnum):
    CHANNEL_NUM = 0   
    CHANNEL_NAME = 1
    FREQUENCY = 2
    DUPLEX = 3
    OFFSET = 4
    TONE_MODE = 5
    TX_TONE = 6
    DCS_TONE = 7
    COMMENT = 8

HEADER_ROW = "Channel, Name, Frequency, Duplex, Offset, Squelch Type, Tone Freq, Comment"

# ----------------------------------------------------------------------
# Global variables - used sparingly to control things like verbosity
# ----------------------------------------------------------------------

# Set this variable to True for debugging output. This can be done with the -v
# or -verbose command line options.
g_verbose = False

# Set this variable to show warnings. This is done using the -w option
g_show_warnings = False

# The default CTCSS tone can be changed on the command line.
g_default_ctcss_tone = DEFAULT_CTCSS_TONE

# The programme can be configured to skip up to nine of the first rows in the
# input file. However, by default the programme only skips
# DEFAULT_NUM_ROWS_TO_SKIP
g_skip_rows = DEFAULT_NUM_ROWS_TO_SKIP

# If this global is set to True, then the application will simply print the help
# message and quit without further processing.
g_print_help_and_exit = False

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------

def read_raw_input(input_filename):
    """Read rows in from the CHIRP CSV and cherrypick the columns
    
    Input - the name of a CHIRP CSV
    Returns - a list of rows and associated column values
    """
    raw_rows = []
    with open(input_filename, newline='') as csv_input:
        ics_csv_reader  = csv.reader(csv_input, delimiter=',', quotechar='"')
        skipped_header = False
        skipped_rows = 0
        for raw_row in ics_csv_reader:

            # Make sure we skip the header row of the CHIRP CSV file.
            if not skipped_header:
                skipped_header = True
                continue

            # Skip the number of rows we've been asked to.
            if skipped_rows < g_skip_rows:
                skipped_rows += 1
                continue

            # Load in only the fields we want from the current CHIRP CSV row.
            truncated_row = [
                raw_row[CHIRP_CSV_COLUMNS.CHANNEL_NUM],
                raw_row[CHIRP_CSV_COLUMNS.CHANNEL_NAME],
                raw_row[CHIRP_CSV_COLUMNS.FREQUENCY],
                raw_row[CHIRP_CSV_COLUMNS.DUPLEX],
                raw_row[CHIRP_CSV_COLUMNS.OFFSET],
                raw_row[CHIRP_CSV_COLUMNS.TONE_MODE],
                raw_row[CHIRP_CSV_COLUMNS.TX_TONE],
                raw_row[CHIRP_CSV_COLUMNS.DTCS_CODE],
                raw_row[CHIRP_CSV_COLUMNS.COMMENT],
            ]
            raw_rows.append(truncated_row)
    return raw_rows

# ------------------------------------------------------------------------------
def process_rows(raw_rows):
    """Creates and formats each row for the output: the website CSV file.
    
    Returns - a list containing rows of channel for the website CSV
    """
    cooked_rows = []
    current_channel_no = 0
    for rrow in raw_rows:
        crow = []

        # First, the channel number. This is unaltered.
        current_channel_no = rrow[WEBSITE_CSV_COLUMNS.CHANNEL_NUM].strip()
        crow.append(current_channel_no)

        # The channel name. Again, unaltered.
        crow.append(rrow[WEBSITE_CSV_COLUMNS.CHANNEL_NAME].strip())

        # Chirp uses six decimal places for frequency. At most we only have four
        # significant digits after the decimal point. Trim down the frequency so
        # that less web real estate is consumed.
        crow.append(str(format_frequency(rrow[WEBSITE_CSV_COLUMNS.FREQUENCY])))

        # This is the frequency offset direction. It implies that this is a
        # repeater channel. Use the content exactly from the CHIRP CSV.
        crow.append(rrow[WEBSITE_CSV_COLUMNS.DUPLEX].strip())

        # There may be an offset in the CHIRP CSV. It goes hand-in-hand with the
        # row above. If there is an offset, make sure it is formatted correctly
        offset = rrow[WEBSITE_CSV_COLUMNS.OFFSET].strip()
        if len(offset) == 0 or float(offset.strip()) == 0.0:
            crow.append('')
        else:
            crow.append(str(format_offset(offset)))

        # If a tone mode is not set, then we do not put a tone frequency in a
        # column. This is counter to what CHIRP does. CHIRP uses a default tone
        # frequency of 88.5Hz for channels that do not use a CTCSS tone and 023
        # for channels that do not use a DCS (in Icom and CHIRP parlance: DTCS)
        # tone.
        mode = rrow[WEBSITE_CSV_COLUMNS.TONE_MODE].strip()
        if mode == DEFAULT_TONE_MODE:
            # No mode, so empty Squelch Type column and empty Tone freq column
            crow.append('')
            crow.append('')
        elif mode == BASIC_TONE_MODE:
            # This case is when the channel only has a transmit tone.
            crow.append(mode)
            crow.append(rrow[WEBSITE_CSV_COLUMNS.TX_TONE].strip())
        elif mode == TONE_SQUELCH_MODE:
            crow.append(mode)
            tone_freq = rrow[WEBSITE_CSV_COLUMNS.TX_TONE].strip()
            crow.append(f"Tx: {tone_freq}; Rx: {tone_freq}")
        elif mode == DCS_TONE_MODE:
            crow.append(WEB_DCS_TONE_MODE_ACRONYM)
            crow.append(rrow[WEBSITE_CSV_COLUMNS.DCS_TONE].strip())
        else:
            # There are no options left. If we see this in the website CSV, then
            # something is wrong parsing the input. N/A was chosen because it is
            # benign should the website be populated with content from an
            # erroneous CHIRP CSV -> website CSV conversion. Better than an
            # error message being propagated.
            warning(f"Uninterpretable mode for channel: {current_channel_no}")
            crow.append('N/A')
            crow.append('')

        # Finally, the comment row
        crow.append(rrow[WEBSITE_CSV_COLUMNS.COMMENT].strip())

        cooked_rows.append(crow)
    return cooked_rows

# ------------------------------------------------------------------------------
def generate_output(output_file, cooked_rows):
    with open(output_file, 'w', newline='') as csvfile:
        csvfile.write(HEADER_ROW + "\n")
        web_writer = csv.writer(csvfile, delimiter=',', quotechar='"', 
            quoting=csv.QUOTE_MINIMAL)
        for row in cooked_rows:
            web_writer.writerow(row)

# ------------------------------------------------------------------------------
def usage():
    """Converts a CHIRP CSV to a CSV that can be input into the CARES Website
    frequency table
    """

    pname = sys.argv[0]
    message = f"""
Usage: {pname} [options] chirp_csv_file target_csv_file

Where options are:
       -h     prints this message to stdout and quits.
       -f n   skips reading the first n [0 - 9] rows of the CHIRP CSV.
       -v     turns on verbose mode.
       -w     turns on warnings mode.
"""
    print(message)

# ------------------------------------------------------------------------------
def verbose(s):
    """For debugging output use only.

    To enable debugging output, set VERBOSE to True
    """

    if g_verbose:
        sys.stderr.write(s + '\n')

# ------------------------------------------------------------------------------
def warning(s):
    """
    To turn on warning messages, set WARNING to True
    """

    if g_show_warnings:
        sys.stderr.write("Warning: " + s + '\n')

# ------------------------------------------------------------------------------
def print_help_message():
    usage()

# ------------------------------------------------------------------------------

def format_frequency(freq):
    """Format a frequency to the correct number of decimal places and represent it
       as a string

    N.B. - this assumes two things. First, the frequency is in MHz. Second, all
    frequencies are represented to 6 decimal places just as CHIRP does.

    """
    frequency_val = float(freq)
    return f"{frequency_val:3.4f}"

# ------------------------------------------------------------------------------
def format_offset(offset_frequency):
    """Format an offset to the correct number of decimal places and represent it
       as a string
    """
    offset = float(offset_frequency)
    return f"{offset:3.1f}"

# ------------------------------------------------------------------------------

def process_options():
    """
    At present there are three command line options. They are:
       -f or --skip-first-rows n: tell the program to skip n rows of the input file.
       -h or --help:              prints a help message and quits.
       -v or --verbose:           to turn on verbose messaging.
       -w or --show-warnings:     turns warning messages on

    Returns the unused arguments passed
    """
    global g_verbose
    global g_show_warnings
    global g_skip_rows
    
    # This list will contain any arguments not processed by the getopts
    # function. For this application, the list may include filenames if the user
    # does not use io redirection at the command line.
    args = []
    try:
        # args will contain any file names once any recognised command line
        # arguments have been pulled out
        opts, args = getopt.getopt(sys.argv[1:], 'f:hvw', 
                                    ['skip-first-rows=', 'help', 'verbose', 'show-warnings'])
    except getopt.GetoptError as err:
        print(f'Invalid command line option: {err}')
        usage()
        sys.exit(2)

    # Process the command line arguments
    for o, a in opts:
        if o in ('-f', '--skip-first-rows'):
            skip_rows = DEFAULT_NUM_ROWS_TO_SKIP
            try:
                skip_rows = int(a)
            except ValueError:
                warning(f'Trying to convert {a} to a positive integer failed. Ignoring')
            if skip_rows >= 0 and skip_rows < 10:
                g_skip_rows = skip_rows
            else:
                warning("The number of rows to skip is out of range "
                        f"(0 .. 9): {skip_rows}. Ignoring")
        elif o in ('-h', '--help'):
            g_print_help_and_exit = True
        elif o in ('-v', '--verbose'):
            g_verbose = True
        elif o in ('-w', '--show-warnings'):
            g_show_warnings = True
        else:
            assert False, f"Unhandled option: {o}"
    return args


# ==============================================================================
#
# Programme entry point
#
# On the command line, the user can provide either:
#
# 1) the name of an input ICS 217A csv file and the name of the output CHIRP csv
# file, or
#
# 2) just an input ICS 217A csv file. The outut CHIRP csv will be sent to
# stdout, or
#
# 3) no file names at all, then the input ICS 217A csv file is presented on
# stdin and the output CHIRP csv content is stream to stdout.
#
# ==============================================================================

if __name__ == '__main__':

    # Process the command line options
    possible_files = process_options()

    if g_print_help_and_exit:
        print_help_message
        sys.exit(0)

    elif len(possible_files) == 2:
        # Prepare the input and output
        raw_rows = read_raw_input(possible_files[0])
        cooked_rows = process_rows(raw_rows)
        generate_output(possible_files[1], cooked_rows)
    else:
        warning("Too few filenames specified on the command line")
        usage()
