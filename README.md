# CARES Technical Committee
## ICS 217A Repository

This repository is used for managing versions of Clackamas County Amateur Radio
Emergency Service's ICS 217A. When this project was started in early 2021, it
was clear that it was difficult to manage the primary source of the CARES
frequency list and produce derivatives of it.

We found that we were losing track of what was the principal copy of the
'truth', i.e. the latest and greatest version of the frequency list and
derivatives were further causing havoc since knowing their lineage was being
lost.

Using a version tracking system like Git makes sense. All of our assets are in
digital form. So, a primary standard version of the frequency plan can be
maintained and checkpointed. From this derivatives can be generated and tagged
as part of that checkpoint.

## Contents of this repository

- An Excel master of the Incident Command System's ICS 217A. **This is the root
  document for all the derived formats**. It's name is always CARES-ICS-217A.xls.
  
  Each version of our ICS-217A has a colour code word associated with it. The
  most recent version is labelled RED.  We iterate through the resistor colour
  code and provide a date for each vintage (see note below). Note that this
  colour is not associated with file names. Publishable updates are collections
  of files tagged with a specific version number and that number is related to
  the colour label.
  
  There is a PDF file that derives from the current master XLS file. This has
  the name CARES-ICS-217A.pdf. Every time a new CARES-ICS-217A.xls is checked
  into this repository, it is mandatory to check in the corresponding PDF
  document. The intent use of this document is to allow operators to create a
  hard copy of the frequency plan for their go-kits (i.e. laminate it).


- CHIRP csv files. These reside in the csv_chirp directory. These are
  derivatives of the Excel master CARES-ICS-217A.xls file.

- A python3 script that generates a CHIRP csv file from the Excel master
  frequency list.


### The resistor colour code and the ICS-217A versions

| Colour | Version date | Tag      | Notes             |
|--------|--------------|----------|-------------------|
| BLACK  | N/A          |          | Unused            |
| BROWN  | 2021-05-22   |          | obsolete          |
| RED    | 2022-03-23   |          | previous version  |
| RED U2 | 2023-02-04   | RED-U2.2 | current version   |
| ORANGE | N/A          |          | Unused            |
| YELLOW |              |          |                   |
| GREEN  |              |          |                   |
| BLUE   |              |          |                   |
| VIOLET |              |          |                   |
| GREY   |              |          |                   |
| WHITE  |              |          |                   |
