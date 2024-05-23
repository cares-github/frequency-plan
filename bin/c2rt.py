#!/usr/bin/env python
#
# Load frequency plan from the CHIRP derivative CSV and produce a CSV
# formatted for RT Systems - specifically YAESU radios.
#
# Andrew Watson (C) 2024

import csv

# These are the headers used by RT systems for specific columns in this
# order.
RT_headers = ["Channel Number",      # Generate this on the fly
                "Receive Frequency",  # 5 decimal places
                "Transmit Frequency", # 5 decimal places
                "Offset Frequency",   # e.g. 600 kHz or 5.00 MHz
                "Offset Direction",   # Plus, Minus, Simplex
                "Operating Mode",     # FM
                "Name",               # Same as CHIRP
                "Tone Mode",          # Tone, T Sql, None, DCS
                "CTCSS",              # e.g. 82.5 Hz
                "DCS",                # e.g. 023
                "PR Freq",            # Default: '1500 Hz'
                "Tx Power",           # Default: 'High'
                "Skip",               # Default: 'Off'
                "Step",               # e.g. '5 kHz'
                "Clock Shift",        # Default: 'Off'
                "Comment"]

# The source CHIRP file uses these headers. Also, these are the keys
# into the dictionaries read in for each row of the CHIRP file.
CHIRP_headers = ["Location",
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
                 "RPT2CALL"]

RT_to_CHIRP_map = {'Channel Number' : 'Location',
                   'Receive Frequency' : 'Frequency',
                   'Operating Mode' : 'Mode',
                   'Name' : 'Name',
                   'Tone Mode' : 'Tone',
                   'CTCSS' : 'rToneFreq',
                   'DCS' : 'DtcsCode',
                   'Step' : 'TStep',
                   'Comment' : 'Comment'}

# ----------------------------------------------------------------------------
def import_CHIRP(input_file: str) -> list[str]:
    raw_chirp_data = []
    with open(input_file, newline='') as csvfile:
        # The CSV file contains incident information. All we need
        # are the station the incident is assigned to, the address
        # and, if stated, the cross street.
        chirp_reader = csv.DictReader(
            csvfile, delimiter=',', quotechar='"')
        for row in chirp_reader:
            # Collect an ordered list of channels in dicts
            raw_chirp_data.append(row)
    return raw_chirp_data

# ----------------------------------------------------------------------------
def c2rt_channel_number(chirp_location: str) -> int:
    return f"{int(chirp_location)}"

# ----------------------------------------------------------------------------
def c2rt_rx_frequency(chirp_frequency: str) -> float:
    return f"{float(chirp_frequency):.5f}"

# ----------------------------------------------------------------------------
def c2rt_tx_frequency(rx_frequency: float, chirp_duplex: str, 
                      chirp_offset: str) -> tuple[str, str]:
    # Convert the string offset freq to a float because we're going to
    # do some maths.
    offset = float(chirp_offset)
    # Assume the channel is simplex
    transmit_frequency = float(rx_frequency)
    offset_direction = "Simplex"

    if chirp_duplex == '+':
        transmit_frequency += offset
        offset_direction = "Plus"
    elif chirp_duplex == '-':
        transmit_frequency -= offset
        offset_direction = "Minus"

    tx_freq_str = f'{float(transmit_frequency):.5f}'
    return (tx_freq_str, offset_direction)

# ----------------------------------------------------------------------------
def c2rt_offset(chirp_offset: str) -> str:
    # All CHIRP frequencies are in megahertz. Need to do some
    # conversion. RT is a bit awkward here.
    offset = float(chirp_offset)

    rt_offset_frequency = ""
    if offset == 0.0:
        rt_offset_frequency = ""
    elif offset < 1.0:
        # Convert to kilohertz
        offset = offset * 1000
        rt_offset_frequency = f"{int(offset)} kHz"
    elif offset >= 1.0:
        rt_offset_frequency = f"{offset:.2f} MHz"
    return rt_offset_frequency

# ----------------------------------------------------------------------------
def c2rt_tone(chirp_tone: str) -> str:
    rt_tone_mode: str = 'None'
    if chirp_tone == 'Tone':
        rt_tone_mode = 'Tone'
    elif chirp_tone == 'TSQL':
        rt_tone_mode = 'T Sql'
    elif chirp_tone == 'DTCS':
        rt_tone_mode = 'DCS'
    return rt_tone_mode

# ----------------------------------------------------------------------------
def c2rt_CTCSS_tone(chirp_tone_mode: str, chirp_rx_tone_freq: str) -> str:
    rt_tone_mode: str = c2rt_tone(chirp_tone_mode)
    tone_freq: float = float(chirp_rx_tone_freq)
    rt_CTCSS_tone = ''
    if rt_tone_mode == 'Tone' or rt_tone_mode == 'T Sql':
        rt_CTCSS_tone = f"{tone_freq:.1f} Hz"
    return rt_CTCSS_tone

# ----------------------------------------------------------------------------
def c2rt_DCS(chirp_dtcs_code: str) -> str:
    rt_dcs: str = ''
    if chirp_dtcs_code == 'DTCS':
        rt_dcs = f"DCS"
    return rt_dcs

# ----------------------------------------------------------------------------
def c2rt_step(chirp_step: str) -> str:
    return f"{chirp_step} kHz"

# ----------------------------------------------------------------------------
def truncate_comments(chirp_comment: str, max_size: int) -> str:
    if max_size < 0 or max_size > 60:
        raise ValueError("Comment maximum size must be between "
                         f"0 and 60 inclusive. Given {max_size}")
    comment_length = len(chirp_comment)
    if comment_length < max_size:
        return chirp_comment
    return chirp_comment[:max_size - 3] + "..."

# ----------------------------------------------------------------------------
def chirp2rt(raw_chirp_data: list[str]) -> list[dict[str : str]]:
    rt_data: list[dict[str: str]] = []
    # Map the chirp data to RT columns. Clean up any formatting.

    for chirp_row in raw_chirp_data:
        rt_row: dict[str : str] = {}

        # RT uses Channel Number whereas CHIRP uses Location
        rt_row['Channel Number'] = c2rt_channel_number(chirp_row['Location'])

        # RT Receive Frequency
        receive_frequency: float = c2rt_rx_frequency(chirp_row['Frequency'])
        rt_row['Receive Frequency'] = receive_frequency

        # RT Transmit Frequency and Offset Direction
        (tx_freq, offset_dir) = c2rt_tx_frequency(receive_frequency,
                                                  chirp_row['Duplex'], 
                                                  chirp_row['Offset'])
        rt_row['Transmit Frequency'] = tx_freq
        rt_row['Offset Direction'] = offset_dir

        # RT Offset Frequency
        rt_row['Offset Frequency'] = c2rt_offset(chirp_row['Offset'])

        # RT Operating Mode - we're explicit here because there could be
        # other modes other than FM in the future.
        rt_row['Operating Mode'] = chirp_row['Mode']

        # RT Name - the channel name. Again, an explicit copy
        rt_row['Name'] = chirp_row['Name']

        # RT Tone Mode
        rt_row['Tone Mode'] = c2rt_tone(chirp_row['Tone'])

        # RT CTCSS
        rt_row['CTCSS'] = c2rt_CTCSS_tone(chirp_row['Tone'], chirp_row['rToneFreq'])

        # RT DCS
        rt_row['DCS'] = c2rt_DCS(chirp_row['DtcsCode'])

        # RT PR Freq. No idea what this is but should be included
        rt_row['PR Freq'] = '1500 Hz'

        # RT transmitting power. Chirp doesn't have this. Set high.
        rt_row['Tx Power'] = 'High'

        # RT Skip - don't allow any channels to be skipped
        rt_row['Skip'] = 'Off'
        
        # RT Step - the frequency step used by the radio dial
        rt_row['Step'] = c2rt_step(chirp_row['TStep'])

        # RT Clock shift - leave off
        rt_row['Clock Shift'] = 'Off'

        # RT Comment
        rt_row['Comment'] = truncate_comments(chirp_row['Comment'], 50)

        # Add the new RT row into the list
        rt_data.append(rt_row)
    return rt_data

# ----------------------------------------------------------------------------
def export_RT(output_file: str, RT_rows: list[dict[str:str]]) -> int:

    with open(output_file, 'w', newline='') as csvfile:
        rt_writer = csv.DictWriter(csvfile, fieldnames=RT_headers)
        rt_writer.writeheader()
        num_rows: int = 1 # including the header
        for row in RT_rows:
            rt_writer.writerow(row)
            num_rows += 1
        return num_rows
# ----------------------------------------------------------------------------
def convert(input_file: str, output_file: str) -> int:
    raw_chirp_content = import_CHIRP(input_file)
    RT_content = chirp2rt(raw_chirp_content)
    num_rows_written: int = export_RT(output_file, RT_content)
    return num_rows_written
# ----------------------------------------------------------------------------
# Programme entry point
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    input_file = '../chirp_csv/2m_and_70cm.csv'
    output_file = '../rt_csv/RT_2m_and_70cm.csv'
#    input_file = '../chirp_csv/1.25m.csv'
#    output_file = '../rt_csv/RT_1.25m.csv'
#    input_file = '../chirp_csv/6m.csv'
#    output_file = '../rt_csv/RT_6m.csv'
#    input_file = '../chirp_csv/GMRS.csv'
#   output_file = '../rt_csv/RT_GMRS.csv'
#    input_file = '../chirp_csv/HF.csv'
#    output_file = '../rt_csv/RT_HF.csv'
    num_rows: int = convert(input_file, output_file)
    print(f'{num_rows} channels converted from CHIRP format to RT Systems format.')
