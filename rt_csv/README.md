# Information regarding the RT Systems CSV files

Unlike CHIRP which uses a standard CSV file format with standard column
headings for all radios, RT Systems treats most radios individually and
has a specific CSV format per radio.

The files included here have been tested with modern Yaesu 2m/70cm
mobile transceivers (FTM 500 and FTM 6000) and they work as expected.
Other Yaesu models may not work with these CSVs as provided. Caveat
emptor.

Kenwood V71 radios permit distinct PL tones for transmit and receive.
Note that these CSVs do not support that feature. There are two choices.
First is to add an Rx CTCSS immediately to the right of the CTCSS
column. For most channels, this column can be left blank for channels
that use Tone or None. However, if a channel uses tone squelch (T Sql in
the Tone Mode column), then you will have to populate the Rx CTCSS
column with the adjacent CTCSS column entry.

Alternatively, fix the channels in radio. This is easy for a TM-V71
([FUNC][T Sel]) but other radios may be trickier.

For 2m/70cm, the following channels are affected:

    EVENT1
    EVENT2
    LO1
    LO2
    MOLA 1

For 1.25m, the following channels are affected:

    C220 1
    C220 9
    C22010
    YELLU1

For GMRS, all channels are affected since GMRS uses tone squelch for all
channels that have a tone set.

If in doubt, seek assistance from someone who knows what they are doing.

Andrew Watson - N1ACW
--