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
# Time-stamp: <2023-02-04 22:19:05 acw> 
# @author: Andrew Watson
# 
# This work is licensed under a CC BY-NC-SA 4.0 international license. 
#

import getopt
import re
import sys

# ----------------------------------------------------------------------
# Constants - all should be capitalised
# ----------------------------------------------------------------------

# The version token file stores a small string that is used to populate the
# channel name in the first or last or both channels in a radio. Be sure to
# update that file when changing the version name for a frequency plan release.

VERSION_TOKEN_FILE = "../CURRENT_VERSION_TOKEN.txt"

# Be sure to update this string as it is prepended to the list of rows and
# added to the end of the list for writing out to the CSV.
CARES_CONTROL_CHANNEL_START = ","
CARES_CONTROL_CHANNEL_END = ",147.120000,+,0.600000,Tone,100.0,100.0,023,NN,FM,5.00,,,,,,,,"

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

# The set of regular CTCSS tones
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

# Regular expression matcher for CTCSS tone strings
CTCSS_TONE_REGEX = re.compile('^\s*[126789][0-9]{1,2}(\.[0-9])?\s*$')

# Why this is CHIRP's default CTCSS tone, I do not know.
DEFAULT_CTCSS_TONE = 88.5

# The set of digital coded squelch tones.
DCS_TONES = {
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

# Regular expression matcher for DCS tone strings
DCS_TONE_REGEX = re.compile('^\s*[dD]?[0-7]?[0-7][1-7]\s*$')

# What CHIRP sets for the default DCS values
DEFAULT_DCS_TONE_CODE = '023'
DEFAULT_DCS_POLARITY  = 'NN'

# What has a given tone field been identified as? These are the options.
TONE_TYPE_UNRECOGNISED = 0
TONE_TYPE_CTCSS        = 100
TONE_TYPE_DCS          = 200

DEFAULT_TONE_MODE = '' # There is no mode - neither Tone, TSQL, DCS etc.
BASIC_TONE_MODE   = 'Tone'
TONE_SQUELCH_MODE = 'TSQL'
DCS_TONE_MODE     = 'DTCS' # CHIRP uses DTCS for this field.

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

# The number of rows/lines of text to skip when running through the input CSV.
g_skip_rows = NUMBER_ROWS_TO_IGNORE_IN_SRC

# The version control channel row information. This starts off incomplete and gets filled in during the setup phase of this programme's execution.
g_control_channel = None

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------

# ------------------------------------------------------------------------------
def usage():
    """Print the usage string onto standard output."""

    pname = sys.argv[0]
    message = f"""
Usage: {pname} [options] ICS_217A_csv CHIRP_csv, or
       {pname} [options]  ICS_217A_csv > CHIRP_csv, or
       {pname} [options] < ICS_217A_csv > CHIRP_csv

Where options are:
       -s     turns on the sentinel row output.
       -t nnn makes nnn the default CTCSS tone
       -v     turns on verbose mode.
       -w     turns on warnings mode.

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

    if g_show_warnings:
        sys.stderr.write("Warning: " + s + '\n')

# ------------------------------------------------------------------------------
def read_ICS_217A(ICS_217A_filename):
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
    with open(ICS_217A_filename, mode='r', newline=None) as ip:
        for input_line in ip:
            if current_line_num >= g_skip_rows:
                raw_input_lines.append(input_line)
            current_line_num += 1

    return raw_input_lines

# ------------------------------------------------------------------------------
def is_ctcss_tone(tone_str):
    """Tries to determine if the input string is a valid CTCSS tone

    tone_str - just a string. Hopefully a CTCSS tone.

    Return - a tuple. First value: either TONE_TYPE_CTCSS or TONE_TYPE_UNRECOGNISED
                      Second value: either a stringified CTCSS tone or the input.
    """

    
    # Make sure the tone string is really there. If it isn't, then report this back to the caller. The input can have no values in this field.
    if tone_str is None:
        warning(f"Tone string was null.")
        return (TONE_TYPE_UNRECOGNISED, g_default_ctcss_tone)
    
    # Clear down white space and look to see if the string has any content. Same
    # thing: if the tone isn't there, that's okay. Report this back to the caller.
    raw_tone = tone_str.strip()
    if len(raw_tone) == 0:
        warning(f"Tone string was zero length. Reverting to default.")
        return (TONE_TYPE_UNRECOGNISED, g_default_ctcss_tone)

    # We have some sort of string. Do a generalised pattern match on the tone
    # candidate string to see if it corresponds to a CTCSS value. The big
    # differentiator between CTCSS tones and DCS tones is that the former
    # contains a decimal point.
    if CTCSS_TONE_REGEX.match(raw_tone) is None:
        warning(f"This tone value is not a CTCSS tone ({raw_tone}).")
        return (TONE_TYPE_UNRECOGNISED, tone_str)

    # See if the raw tone can be converted to a number. If not, then fall
    # back on the default tone value.
    tone_value = 0
    try:
        tone_value = float(raw_tone)
    except ValueError:
        warning(f"Not a CTCSS tone: {raw_tone}.")
        return (TONE_TYPE_UNRECOGNISED, tone_str)

    if tone_value in STANDARD_CTCSS_TONES:
        # A valid CTCSS tone was found.
        verbose(f'Registered a valid CTCSS tone: {tone_value}Hz.')
        return (TONE_TYPE_CTCSS, str(tone_value))

    elif tone_value in EXTENDED_CTCSS_TONES:
        warning(f"Extended CTCSS tone encountered: {tone_value}Hz.")
        return (TONE_TYPE_CTCSS, str(tone_value))
    else:
        warning("Looks like a CTCSS tone but does not match the known "
                f"set of correct values: {raw_tone}")
    return (TONE_TYPE_UNRECOGNISED, tone_str)

# ------------------------------------------------------------------------------
def is_dcs_tone(tone_str):
    """Tries to determine if the input string is a valid DCS tone

    tone_str - just a string. Hopefully a DCS tone.

    Returns a tuple. The first element tells you if the input is a DCS tone or not. These are indicated by TONE_TYPE_DCS or TONE_TYPE_UNRECOGNIED respectively. The second element is the tone in string form ([0-9][1-9]).
    """

    # Make sure the tone string is really there
    if tone_str is None:
        warning("Tone string was null. Reverting to default DCS value: "
                f"{DEFAULT_DCS_TONE_CODE}.")
        return (TONE_TYPE_UNRECOGNISED, tone_str)

    # Check for a zero-length string    
    raw_tone = tone_str.strip()
    if len(raw_tone) == 0:
        warning(f"Tone string was zero length.")
        return (TONE_TYPE_UNRECOGNISED, tone_str)

    # Check the generalised pattern for a DCS tone
    if DCS_TONE_REGEX.match(raw_tone) is None: 
        warning(f"This value is not a valid DCS tone ({raw_tone}).")
        return (TONE_TYPE_UNRECOGNISED, tone_str)

    # We should have something close to a DCS value here. Now check it to make
    # sure it really is.

    tone_str_len = len(raw_tone)

    # Test the most likely circumstance first - a valid length.
    if tone_str_len == 4:
        # DCS tones often start with a capital D. They are not supposed to start with a lower case d, but just give the benefit of the doubt.
        if raw_tone[0] in ('D', 'd') and raw_tone[1:] in DCS_TONES:
            verbose(f"Got a valid 4-character DCS tone: {raw_tone}")
            return (TONE_TYPE_DCS, raw_tone)
        else:
            warning(f"This value is not a valid DCS tone: {raw_tone}")
            return (TONE_TYPE_UNRECOGNISED, tone_str)
    # Perhaps the D wasn't prepended - check to see if digits are present
    elif tone_str_len == 3:
        if raw_tone in DCS_TONES:
            verbose(f"Got a valid 3-character DCS tone: {raw_tone}")
            return (TONE_TYPE_DCS, raw_tone)
        else:
            warning(f"This value is not a valid DCS tone: {raw_tone}")
            return (TONE_TYPE_UNRECOGNISED, tone_str)
    elif tone_str_len == 2:
        if '0' + raw_tone in DCS_TONES:
            verbose(f"Got a valid 2-character DCS tone: {raw_tone}")
            return (TONE_TYPE_DCS, raw_tone)
        else:
            warning(f"This value is not a valid DCS tone: {raw_tone}")
            return (TONE_TYPE_UNRECOGNISED, tone_str)
    else:
        warning(f"This value is not a valid DCS tone: {raw_tone}")
    return (TONE_TYPE_UNRECOGNISED, tone_str)

# ------------------------------------------------------------------------------
def parse_tone(tone_str):
    """Figure out what tone type has been presented

    The tone could a CTCSS tone, a DCS tone or unrecognisable as a tone value.
    
    We assume that there's nothing there. If a CTCSS tone is spotted, this is
    flagged as TONE_TYPE_CTCSS. If it's DCS, then TONE_TYPE_DCS otherwise
    TONE_TYPE_UNRECOGNISED
    """
    # First, check for a CTCSS style tone
    tone_type, tone_value = is_ctcss_tone(tone_str)
    if tone_type == TONE_TYPE_CTCSS:
        return (tone_type, tone_value)
    
    # CTCSS didn't work. Let's try a DCS tone
    tone_type, tone_value = is_dcs_tone(tone_str)
    if tone_type == TONE_TYPE_DCS:                
        return (tone_type, tone_value)

    # The tone is not valid
    return (TONE_TYPE_UNRECOGNISED, None)

# ------------------------------------------------------------------------------
def parse_tones(tx_tone_str, rx_tone_str):
    """
    The ICS 217A refers to tones with reference to the local user's station. If
    the user has to transmit a tone to access a repeater or work simplex, then
    this is known as the tx_tone in this function.

    """
    tone_mode = DEFAULT_TONE_MODE
    tx_ctcss_tone = g_default_ctcss_tone
    rx_ctcss_tone = g_default_ctcss_tone
    tx_dcs_code = DEFAULT_DCS_TONE_CODE
    rx_dcs_code = DEFAULT_DCS_TONE_CODE


    (tx_tone_type, tx_tone_value) = parse_tone(tx_tone_str)
    (rx_tone_type, rx_tone_value) = parse_tone(rx_tone_str)

    if tx_tone_type == TONE_TYPE_CTCSS:
        # The local station has to transmit a tone to access the remote
        # station.
        tx_ctcss_tone = tx_tone_value
        if rx_tone_type == TONE_TYPE_CTCSS:
            # The remote station also sends a tone. This system uses tone
            # squelch.
            tone_mode = TONE_SQUELCH_MODE
            # It is possible that a different tone is used for local receive,
            # but most radios don't support this so this is unlikely to be
            # different from the tx_tone.
            rx_ctcss_tone = rx_tone_value
        else:
            tone_mode = BASIC_TONE_MODE

    elif tx_tone_type == TONE_TYPE_DCS:
        tx_dcs_tone = tx_tone_value
        tone_mode = DCS_TONE_MODE
        if rx_tone_type == TONE_TYPE_DCS:
            rx_dcs_tone = rx_tone_value

    return (tone_mode, tx_ctcss_tone, rx_ctcss_tone, tx_dcs_code, rx_dcs_code)

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
        chirp_dcs_code = DEFAULT_DCS_TONE_CODE
        chirp_dcs_polarity = DEFAULT_DCS_POLARITY
        chirp_remote_ctcss_tone = DEFAULT_CTCSS_TONE
        chirp_local_ctcss_tone = DEFAULT_CTCSS_TONE

        # The local station's transmit tone is: ics_row[6]
        # The local station's receive tone is: ics_row[7]
        (chirp_tone_mode,
         chirp_local_ctcss_tone,
         chirp_remote_ctcss_tone,
         chirp_dcs_code,
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
             chirp_tone_mode,          # e.g. Tone, TSQL, DCS, etc.
             chirp_local_ctcss_tone,   # rToneFreq - sent by local to open the remote
             chirp_remote_ctcss_tone,  # cToneFreq - If tone squelch is being used.
             chirp_dcs_code,          # Set if DCS is being used
             chirp_dcs_polarity,      # Usually NN - as previous.
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
class NumberOfFilesError(Exception):
    """Raised when the user passes in the wrong number of files on the command line.
    """
    pass

def get_filenames(args):
    """Checks that the user passed in some filenames

    This function currently bails out if the wrong number of files were specified.

    Returns - a tuple containing the input file name and output file name
    """
    input_filename = None
    output_filename = None
    if len(args) == 2:
        input_filename, output_filename = args[0], args[1]
    else:
        # TODO - use proper Python logging
        print ("Incorrect number of filenames. There should be an input and output file specified")
        raise NumberOfFilesError()
    return (input_filename, output_filename)

# ------------------------------------------------------------------------------

def generate_output(output_filename, rows, use_control_channel):
    """Writes the generated rows out to the specified file.

    output_filename - just like it says
    rows - the channel rows to write out to output_filename
    use_control_channel - if True, then the control channel is written out.
    """
    with open(output_filename, 'w', newline=None) as op:
        op.write(CHIRP_CSV_HEADER_FIELDS + '\n')

        # Put in the row that tells us this is the particular colour plan.
        if use_control_channel:
            op.write("0" + g_control_channel + '\n')

        last_row = ""
        for r in rows:
            # Get the location (i.e. row) number for this record.
            last_row = r[0]
            op.write(",".join([str(field) for field in r]) + '\n')

        # Put in the row that tells us this is the particular colour plan.
        if use_control_channel:
            tail_row = int(last_row) + 1
            op.write(f"{tail_row}" + g_control_channel + '\n')

# ------------------------------------------------------------------------------
def load_version_channel_name():
    """Loads and uses the version channel name from a token file in a specific location

    Reads in the file (hardwired path/name stored in VERSION_TOKEN_FILE) and uses that content, if it can to build up the version channel row information.

    This function will shut the programme down if the file is not found or, if it is found, the data does not match the required pattern.
    """
    global g_control_channel
    # A bunch of regular expressions. These only get used once, so it is fine to
    # keep them hidden away in this function definition.
    #
    # Matches any line that has either no or only whitespace.
    blank_line_re = re.compile('^\s*$')

    # Comment lines in the version token file start with a # sign. We'll assume
    # that some space characters could precede the # and ignore those..
    comment_line_re = re.compile('^\s*#.*$')

    # The regexp that matches the version token. Basically this can be between 1
    # and 6 alphanumeric characters and an underscore. (\w = [a-zA-Z0-9_])
    version_token_re = re.compile('^\s*\w{1,6}\s*$')

    with open(VERSION_TOKEN_FILE, newline='') as version_file:
        for line in version_file:
            if blank_line_re.match(line):
                # Ignore blank lines
                continue
            elif comment_line_re.match(line):
                # ignore comment lines
                continue
            elif version_token_re.match(line):
                # Should have the version channel name. Check that this conforms
                # to the specification of just one to six characters.
                g_control_channel = CARES_CONTROL_CHANNEL_START +  line.strip() + CARES_CONTROL_CHANNEL_END
                break
            else:
                line.strip()
                warning(f"Unexpected content in the version token file: {line}")
                sys.exit(11)

# ------------------------------------------------------------------------------
def process_options():
    """
    At present there are five command line options. They are:
       -f or --skip-first-rows n: tell the programme to skip n rows of the input file.
       -c or --control_ch:        tells the programme to insert the control channel.
       -v or --verbose:           to turn on verbose messaging.
       -t n or --tone n:          to provide a non-default tone. The tone must be a 
                                  valid CTCSS   tone (no DCS - that's a corner case) or zero.  
       -w or --show-warnings:     turns warning messages on

    Returns True if the version name control channel row is to be displayed.
    """
    global g_verbose
    global g_default_ctcss_tone
    global g_show_warnings
    global g_skip_rows
    
    # Assume that there are no command line options
    turn_on_control_channel = False

    # This list will contain any arguments not processed by the getopts
    # function. For this application, the list may include filenames if the user
    # does not use io redirection at the command line.
    args = []
    try:
        # args will contain any file names once any recognised command line
        # arguments have been pulled out
        opts, args = getopt.getopt(sys.argv[1:], 'f:cvt:w', 
                                    ['skip-first-rows=', 'control_ch', 'verbose', 
                                    'tone=', 'show-warnings'])
    except getopt.GetoptError as err:
        print(f'Invalid command line option: {err}')
        usage()
        sys.exit(2)

    # Process the command line arguments
    for o, a in opts:
        if o in ('-f', '--skip-first-rows'):
            g_skip_rows = 0
            skip_rows = 0
            try:
                skip_rows = int(a)
            except ValueError:
                warning(f'Trying to convert {a} to a positive integer failed. Ignoring')
                skip_rows = NUMBER_ROWS_TO_IGNORE_IN_SRC
            if skip_rows >= 0 and skip_rows < 10:
                g_skip_rows = skip_rows
            else:
                warning("The number of rows to skip is out of range "
                        f"(0 .. 9): {skip_rows}. Ignoring")
        elif o in ('-c', '--control_ch'):
            turn_on_control_channel = True
        elif o in ('-v', '--verbose'):
            g_verbose = True
        elif o in ('-w', '--show-warnings'):
            g_show_warnings = True
        elif o in ('-t', '--tone'):
            (tone_type, tone_value) = parse_tone(a)
            if tone_type == TONE_TYPE_CTCSS:
                g_default_ctcss_tone = tone_value
                verbose(f'Default CTCSS tone has been set to: {g_default_ctcss_tone}Hz')
        else:
            assert False, f"Unhandled option: {o}"

    return turn_on_control_channel, args


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
    use_control_channel, args = process_options()

    # Figure out what files we're working with.
    try:
        input_filename, output_filename = get_filenames(args)
    except NumberOfFilesError:
        # The wrong number of files were specified on the command line.
        sys.exit(-1)

    # Load the current CARES frequency plan version information. This may be
    # used as a channel name for the first channel in the 2m/70cm list (if the
    # user of the programme  chooses). It can also be found as the last channel
    # too.
    load_version_channel_name()

    # Load the content from the ICS 217A exported from Excel
    raw_input_lines = read_ICS_217A(input_filename)

    # Interpret the ICS 217A and clean up the data from this file ready for the
    # conversion to CHIRP format.
    cooked = ics_parse(raw_input_lines)
    generate_output(output_filename, cooked, use_control_channel)
