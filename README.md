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

- An Excel master of the ICS-217A. Each version of our ICS-217A has a colour
  code word associated with it. The most recent version is labelled BROWN.  We
  iterate through the resistor colour code and provide a date for each
  vintage (see note below).
  

- A python3 script that generates a CHIRP csv file from the Excel master
  frequency list.

- Any derivatives, like the above-mentioned CHIRP csv file.


### The resistor colour code and the ICS-217A versions

| Colour | Version date | Notes             |
|--------|--------------|-------------------|
| BLACK  | N/A          | Unused            |
| BROWN  | 2021-05-22   | (current version) |
| RED    |              |                   |
| ORANGE |              |                   |
| YELLOW |              |                   |
| GREEN  |              |                   |
| BLUE   |              |                   |
| VIOLET |              |                   |
| GREY   |              |                   |
| WHITE  |              |                   |
