#!/usr/bin/env python3
#
# Programme that converts a CARES frequency plan into a CHIRP compatible CSV
# file.
#
# The input file to this programme is an exported CSV that comes directly from
# the Excel source document. Note that an exported CSV will potentially need
# some clean up. Sometimes comments are not quoted, some channels are not
# numbered. These will also need manual intervention.
#
# The programme will insert a sentinel row at the beginning and at the end of a
# generated CHIRP csv. This is only really useful for the 2m and 70cm version.
#
# Time-stamp: <2023-02-04 22:19:05 acw> @author: Andrew Watson
# This work is licensed under a CC BY-NC-SA 4.0 international license. 
#

import getopt
import sys

# ----------------------------------------------------------------------
# Constants - all should be capitalised
# ----------------------------------------------------------------------

# Be sure to update this string as it is prepended to the list of rows and
# added to the end of the list for writing out to the CSV.
CARES_SENTINEL_ROW = ",RED_U2,147.120000,+,0.600000,Tone,100.0,100.0,023,NN,FM,5.00,,,,,,,,"

# Set this variable to True for debugging output. This can be done with the -v
# or -verbose command line options.
g_verbose = False

# Send any warning messages to stderr if this switch is set to True.
WARNING = True

# The ICS 217A file emitted from Excel contains a certain number of header
# rows. These are ignored and not added to the resultant CHIRP csv file. The
# following value hold that number of header rows to skip over at the top of the
# file.
#
# LAST TIME THIS WAS RUN - THE CSV WAS MANUALLY STRIPPED OF ITS HEADERS (2022-11-05)
# NUMBER_ROWS_TO_IGNORE_IN_SRC = 3
NUMBER_ROWS_TO_IGNORE_IN_SRC = 0

# The ICS 217A has 11 columns. Some contain data, some don't have to.
ICS_217A_NUMBER_OF_COLUMNS = 11

# The CHIRP CSV file header fields. This is in list form rather than a string
# just to make it easier to see the individual fields and simplifies rearranging
# them should reusing this code for another format be necessary.
#
# N.B. This is the order, left to right, that CHIRP expects its data to be in.
# Currently, CHIRP does not use URCALL, RPT1CALL and RPT2CALL as far as I can
# tell.

CHIRP_CSV_HEADER_FIELDS = ",".join(["Location",
                                    "Name",
                                    "Frequency",
                                    "Duplex",
                                    "Offset",
                                    "Tone",
                                    "rToneFreq",
                                    "cToneFreq",
                                    "DtcsCode",
                                    "DtcsPolarity",
                                    "Mode",
                                    "TStep",
                                    "Skip",
                                    "Comment",
                                    "URCALL",
                                    "RPT1CALL",
                                    "RPT2CALL"])

# This is the first channel number for CHIRP This is known as the 'Location'
# column value in CHIRP vocabulary.
#
# TODO - allow a command line option to override this
CHIRP_CHANNEL_NO_START = 0

DEFAULT_FREQUENCY = 147.12

DEFAULT_MODULATION = 'FM'
DEFAULT_SKIP = '' # Should the input channel be skipped. No - we take everything.

# Some radios have a problem with the tuning step being 6.25 kHz. We're going to
# stick to 5.0 kHz for all.
DEFAULT_TUNE_STEP = '5.00'

DEFAULT_COMMENTS = "\"N/A\""

# A set of CTCSS tones
STANDARD_CTCSS_TONES = {
    67.0,  69.3,  71.9,  74.4,  77.0,
    79.7,  82.5,  85.4,  88.5,  91.5,
    94.8,  97.4,  100.0, 103.5, 107.2,
    110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4,
    156.7, 162.2, 167.9, 173.8, 179.9,
    186.2, 192.8, 203.5, 206.5, 210.7,
    218.1, 225.7, 229.1, 233.6, 241.8,
    250.3, 254.1}

EXTENDED_CTCSS_TONES = {159.8, 165.5, 171.3, 177.3, 183.5, 189.9, 196.6, 199.5}

DTCS_TONES = {
    '023', '025', '026', '031', '032', '036', '043', '047',
    '051', '053', '054', '065', '071', '072', '073', '074',
    '114', '115', '116', '122', '125', '131', '132', '134',
    '143', '145', '152', '155', '156', '162', '165', '172',
    '174', '205', '212', '223', '255', '226', '243', '244',
    '245', '246', '251', '252', '255', '261', '263', '265',
    '266', '271', '274', '306', '311', '315', '325', '331',
    '332', '343', '346', '351', '356', '364', '365', '371',
    '411', '412', '413', '423', '431', '432', '445', '446',
    '452', '454', '455', '462', '464', '465', '466', '503',
    '506', '516', '523', '565', '532', '546', '565', '606',
    '612', '624', '627', '631', '632', '654', '662', '664',
    '703', '712', '723', '731', '732', '734', '743', '754'}

# Why this is the default tone, I do not know.
DEFAULT_CTCSS_TONE = '88.5'
DEFAULT_DTCS_TONE_CODE = '023'
DEFAULT_DTCS_POLARITY = 'NN'

# What has a given tone field been identified as? These are the options.
NO_TONE_IDENTIFIED = 0
CTCSS_TONE_IDENTIFIED = 100
DTCS_TONE_IDENTIFIED = 200

DEFAULT_TONE_MODE = '' # There is no mode - neither Tone, TSQL, DTCS etc.
BASIC_TONE_MODE   = 'Tone'
TONE_SQUELCH_MODE = 'TSQL'
DTCS_TONE_MODE = 'DTCS'

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------

# ------------------------------------------------------------------------------
def usage():
    """Print the usage string onto standard output."""

    pname = sys.argv[0]
    message = f"""
Usage: {pname} [-s | -v] ICS_217A_csv CHIRP_csv, or
       {pname} [-s | -v]  ICS_217A_csv > CHIRP_csv, or
       {pname} [-s | -v] < ICS_217A_csv > CHIRP_csv

Where:
       -s turns on the sentinel row output.
       -v turns on verbose mode.

       ICS_217A_csv: is the name of the file generated by Excel when the CARES
                     frequency plan is exported as a comma separated value file.
          CHIRP_csv: is the output file name. This will be in a CHIRP CSV format.
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

    if WARNING:
        sys.stderr.write("Warning: " + s + '\n')

# ------------------------------------------------------------------------------
def setup_io(possible_files):
    """Find out the filenames the user wants to work with, then open them.

    possible_files - a list of files for input and output. If this parameter is a
    zero-lengthed list, then there were no files specified on the command line.
    returns an open file object for input and output.
    """

    # Assume that the input and output streams are being used.
    input_file = sys.stdin
    output_file = sys.stdout

    if len(possible_files) == 0:
        # Just the programme name and possibly command line arguments specified.
        # Assume that the input and output are on stdin and stdout respectively.
        pass
    elif len(possible_files) == 1:
        # There's only one argument, then that means the input file was
        # specified. Output goes to stdout
        try:
            input_file = open(possible_files[0], 'r')
        except OSError:
            print(sys.argv[0] + ": Could not open input ICS 217A csv file: " + possible_files[0])
            sys.exit(3)

    elif len(possible_files) == 2:
        # Both files are specified. First attempt to open the input file.
        try:
            verbose(f"Opening the file: {possible_files[0]} for reading")
            input_file = open(possible_files[0], 'r')
        except OSError:
            print(sys.argv[0] + ": Could not open input ICS 217A csv file: " + possible_files[0])
            exit(4)

        # Successfully opened the input file. Now attempt to open the output file.
        try:
            verbose(f"Opening the file: {possible_files[1]} for writing")
            output_file = open(possible_files[1], 'w')
        except OSError:
            print(sys.argv[0] + ": Could not open CHIRP output csv file: " + possible_files[1])
            exit(5)

    else:
        # More arguments specified than can be handled. Let the user know and bail out.
        print(sys.argv[0] + ": Error: too many command line arguments")
        usage()
        exit(6)

    return (input_file, output_file)

# ------------------------------------------------------------------------------
def read_ICS_217A(ICS_217_file):
    """
    Reads in the frequency data from the CARES ICS 217A

    The ICS 217A data is provided as a CSV export from Excel.

    Strip header rows from the ICS 217A file first This list holds the rows
    from the input. This is easiest by iterating over the file and skipping
    the first few lines. You can do this manually - but make adjustments
    below. Last time this was run, the headers were stripped from the CSV.

    N.B. The first row written to this list contains the column headers.

    Output: a list of channel data still in the ICS 217A order
    """
    raw_input_lines = []
    current_line_num = 0

    for input_line in ICS_217_file:
        if current_line_num >= NUMBER_ROWS_TO_IGNORE_IN_SRC:
            raw_input_lines.append(input_line)
        current_line_num += 1
    return raw_input_lines


# ------------------------------------------------------------------------------
def parse_tone(tone_str):
    #
    # The tone could either be nothing, a CTCSS tone, or a DTCS tone.
    #
    # We assume that there's nothing there. If a CTCSS tone is spotted, this is
    # flagged as CTCSS_TONE_IDENTIFIED. If it's DTCS, then DTCS_TONE_IDENTIFIED
    #
    tone_value = None
    tone_type = NO_TONE_IDENTIFIED
    tone_warning = False

    raw_tone = tone_str.strip()
    if len(raw_tone) > 0:
        # See if the raw tone can be converted to a number. If not, then fall
        # back on the default tone value.
        test_for_dtcs = False
        try:
            tone_value = float(raw_tone)
            if tone_value in STANDARD_CTCSS_TONES:
                # A valid CTCSS tone was found.
                tone_type = CTCSS_TONE_IDENTIFIED
            elif tone_value in EXTENDED_CTCSS_TONES:
                warning(f"Extended CTCSS receive tone encountered: {tone_value}.")
                tone_type = CTCSS_TONE_IDENTIFIED
                tone_warning = True
        except ValueError:
            tone_value = DEFAULT_CTCSS_TONE
            test_for_dtcs = True

        # Maybe it's a DTCS code. Those start with the character D
        if test_for_dtcs and raw_tone[0] == 'D':
            # The current CARES documentation protocol is to define a DTCS code
            # with a leading 'D' followed by three digits.
            tone_value = raw_tone[1:]
            if tone_value in DTCS_TONES:
                tone_type = DTCS_TONE_IDENTIFIED
            else:
                warning(f"Value '{tone_value}' doesn't appear to be a valid DTCS tone.")
    return (tone_type, tone_value, tone_warning)

# ------------------------------------------------------------------------------
def parse_tones(tx_tone_str, rx_tone_str):
    """
    The ICS 217A refers to tones with reference to the local user's station. If
    the user has to transmit a tone to access a repeater or work simplex, then
    this is known as the tx_tone in this function.

    """
    tone_mode = DEFAULT_TONE_MODE
    tx_ctcss_tone = DEFAULT_CTCSS_TONE
    rx_ctcss_tone = DEFAULT_CTCSS_TONE
    tx_dtcs_code = DEFAULT_DTCS_TONE_CODE
    rx_dtcs_code = DEFAULT_DTCS_TONE_CODE


    (tx_tone_type, tx_tone_value, tx_tone_warning) = parse_tone(tx_tone_str);
    (rx_tone_type, rx_tone_value, rx_tone_warning) = parse_tone(rx_tone_str);

    if tx_tone_type == CTCSS_TONE_IDENTIFIED:
        # The local station has to transmit a tone to access the remote
        # station.
        tx_ctcss_tone = tx_tone_value
        if rx_tone_type == CTCSS_TONE_IDENTIFIED:
            # The remote station also sends a tone. This system uses tone
            # squelch.
            tone_mode = TONE_SQUELCH_MODE
            # It is possible that a different tone is used for local receive,
            # but most radios don't support this so this is unlikely to be
            # different from the tx_tone.
            rx_ctcss_tone = rx_tone_value
        else:
            tone_mode = BASIC_TONE_MODE

    elif tx_tone_type == DTCS_TONE_IDENTIFIED:
        tx_dtcs_tone = tx_tone_value
        tone_mode = DTCS_TONE_MODE
        if rx_tone_type == DTCS_TONE_IDENTIFIED:
            rx_dtcs_tone = rx_tone_value

    return (tone_mode, tx_ctcss_tone, rx_ctcss_tone, tx_dtcs_code, rx_dtcs_code)

# ------------------------------------------------------------------------------

def cleanse_comments(raw_comments):
    if(isinstance, raw_comments, str):
        clean_comments = raw_comments.strip()
        clean_comments.replace(',','')
        return "\"" + clean_comments + "\""
    return DEFAULT_COMMENTS

# ------------------------------------------------------------------------------
def format_frequency(freq):
    """Format a frequency to the correct number of decimal places and represent it
       as a string

    N.B. - this assumes two things. First, the frequency is in MHz. Second, all
    frequencies are represented to 6 decimal places just as CHIRP does.

    """
    return f"{freq:3.6f}"

# ------------------------------------------------------------------------------
def parse_frequency(raw_frequency):
    """Tries to parse the frequency field in a row from the ICS 217A

    If there is an error in the frequency, DEFAULT_FREQUENCY is returned.
    """
    cooked_frequency = DEFAULT_FREQUENCY
    if isinstance(raw_frequency, str):
        wip_frequency = raw_frequency.strip()
        try:
            cooked_frequency = float(wip_frequency)
        except ValueError:
            # It's not a number, so we have to rely on writing the default frequency
            warning(f"Unrecognisable frequency value: {ics_row[2]} for {ics_row[1]}.")
    return format_frequency(cooked_frequency)

# ------------------------------------------------------------------------------
def is_null_row(channel_name, frequency):
    """True if it looks like this row is intentionally blank

    Blankness is determined based on the frequency and it's value in the row as
    well as the name of the channel.
    """
    if isinstance(channel_name, str) and len(channel_name.strip()) == 0:
        # The name is blank. All rows must have a channel name.
        return True
    return False

# ------------------------------------------------------------------------------
def ics_parse(raw_ics_data):
    """
    Cleans up the ICS 217A content and parses out interesting pieces of data,
    such as the sign of the offset and DCS tone, if any.

    """
    chirp_cooked_rows = []
    ics_row_counter = 1
    for line in raw_ics_data:
        # Break the ICS line up into pieces
        ics_row = line.split(',')
        if len(ics_row) < 10:
            warning(f"Row {ics_row[0]} does not have enough columns: {len(ics_row)}")
            # Ignore lines that do not have sufficient columns
            ics_row_counter += 1
            continue
        if is_null_row(ics_row[1], ics_row[2]):
            # Found a blank row. Quietly ignore it
            warning(f"A null row was encountered at row: {ics_row_counter}")
            ics_row_counter += 1
            continue

        #
        # Assume we got a decent row of content from the ICS 217A. Convert the
        # row's column values into parsed forms suitable for CHIRP
        #

        # First up, the channel number. CHIRP calls this 'location'.
        chirp_location = ics_row[0].strip()

        # The name of this channel. For example, CLAC01
        chirp_name = ics_row[1]

        chirp_frequency = parse_frequency(ics_row[2])

        # CHIRP does not use a transmit frequency. It deduces it from the
        # receive frequency, offset and Duplex sign. So column 3 in the CARES
        # frequency list is ignored.

        # Compute the transmit offset and frequency if anything. Assume that the
        # channel is simplex with no offset.
        t_offset = 0.0
        chirp_duplex_offset_sign = ''
        if len(ics_row[4].strip()) > 0:
            # A frequency offset was specified. This is a duplex channel.
            t_offset = float(ics_row[4])
            if t_offset > 0:
                chirp_duplex_offset_sign = '+'
            else:
                chirp_duplex_offset_sign = '-'
        chirp_offset = format_frequency(abs(t_offset))


        # This will almost certainly be 'FM'
        chirp_modulation = DEFAULT_MODULATION

        # Sort out the receive tones for CHIRP. Make some assumptions based on
        # how CHIRP does things, as to what are reasonable defaults.

        chirp_tone_mode = DEFAULT_TONE_MODE
        chirp_dtcs_code = DEFAULT_DTCS_TONE_CODE
        chirp_dtcs_polarity = DEFAULT_DTCS_POLARITY
        chirp_remote_ctcss_tone = DEFAULT_CTCSS_TONE
        chirp_local_ctcss_tone = DEFAULT_CTCSS_TONE

        # The local station's transmit tone is: ics_row[6]
        # The local station's receive tone is: ics_row[7]
        (chirp_tone_mode,
         chirp_local_ctcss_tone,
         chirp_remote_ctcss_tone,
         chirp_dtcs_code,
         not_used) = parse_tones(ics_row[6], ics_row[7])


        chirp_description = cleanse_comments(ics_row[8])
        chirp_changes = ics_row[9]
        ics_row_counter += 1

        chirp_cooked_rows.append(
            [chirp_location,           # Location (i.e. row number)
             chirp_name,               # Name
             chirp_frequency,          # Remote's listening frequency
             chirp_duplex_offset_sign, # Duplex
             chirp_offset,             # Offset
             chirp_tone_mode,          # e.g. Tone, TSQL, DTCS, etc.
             chirp_local_ctcss_tone,   # rToneFreq - sent by local to open the remote
             chirp_remote_ctcss_tone,  # cToneFreq - If tone squelch is being used.
             chirp_dtcs_code,          # Set if DTCS is being used
             chirp_dtcs_polarity,      # Usually NN - as previous.
             chirp_modulation,         # Almost always FM
             DEFAULT_TUNE_STEP,        # This is the minimum increment for the
                                       # tuning dial.
             DEFAULT_SKIP,             # We don't skip anything.
             chirp_description,        # The comment.
             "",                       # URCALL - not used
             "",                       # RPT1CALL - not used
             ""])                      # RPT2CALL - not used
    return chirp_cooked_rows

# ------------------------------------------------------------------------------

def generate_output(rows, use_sentinel):
    """
    Prints the generated CSV rows to standard output.
    """
    print(CHIRP_CSV_HEADER_FIELDS)

    # Put in the row that tells us this is the particular colour plan.
    if use_sentinel:
        print("0" + CARES_SENTINEL_ROW)

    last_row = ""
    for r in rows:
        # Get the location (i.e. row) number for this record.
        last_row = r[0]
        print(",".join([str(field) for field in r]))

    # Put in the row that tells us this is the particular colour plan.
    if use_sentinel:
        tail_row = int(last_row) + 1
        print(f"{tail_row}" + CARES_SENTINEL_ROW)

# ------------------------------------------------------------------------------
def process_options():
    """
    At present there is only one command line option and that's
    -s or --sentinel to turn on the sentinel row.

    Returns True if the sentinel row is to be displayed.
    """

    # Assume that there are no command line options
    turn_on_sentinel = False

    # This list will contain any arguments not processed by the getopts
    # function. For this application, the list may include filenames if the user
    # does not use io redirection at the command line.
    args = []
    try:
        # args will contain any file names once any recognised command line
        # arguments have been pulled out
        opts, args = getopt.getopt(sys.argv[1:], 'sv', ['sentinel', 'verbose'])
    except getopt.GetoptError as err:
        print(f'Invalid command line option: {err}')
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ('-s', '--sentinel'):
            print('Turning on sentinel')
            turn_on_sentinel = True
        elif o in ('-v', '--verbose'):
            g_verbose = True
        else:
            assert False, f"Unhandled option: {o}"

    return turn_on_sentinel, args


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
    use_sentinel, possible_files = process_options()

    # Prepare the input and output
    input_file, output_file = setup_io(possible_files)

    # Load the content from the ICS 217A exported from Excel
    raw_input_lines = read_ICS_217A(input_file)

    # Interpret the ICS 217A and clean up the data from this file ready for the
    # conversion to CHIRP format.
    cooked = ics_parse(raw_input_lines)
    generate_output(cooked, use_sentinel)

    # Close file descriptors
    input_file.close()
    output_file.close()
