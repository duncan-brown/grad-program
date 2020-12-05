# Physics Graduate Program Helper Scripts

This repository contains scripts to help keep track of the academic standing of students in the Syracuse University Physics Graduate Program. The main program is `transcript.py` which parses the PDF advising transcripts produced by MySlice.

## Using the Scripts

To run the parsing script:
```
docker run -it --rm --name grad-program grad-program [OPTIONS]
```
where `[OPTIONS]` are:

| Option                   | Example Argument           | Description  |
| ------------------------ | -------------------------- | ------------ |
| `--current-semester`     | `Fall 2020`                | Name of current semester to parse pending grades (no default)  |
| `--transcript-file`      | `Transcripts.PDF`          | PDF file containing MySlice advising transcripts (default is `Transcripts.PDF`)  |
| `--active-student-file`  | `Active Student Data.csv`  | CSV file contaiing active student data from MySlice query  (default is `Active Student Data.csv`) |
| `--output-file`          | `report.csv`               | CSV file contaiing report on students for upload to Teams (default is `report.csv`)  |
| `--log-level`            | `warning`                  | Logging level as descrived below  |

The optional argument `--log-level` can be used to print more or less information about each student. Valid options to `--log-level` are:

| Level       | Description  | 
| ----------- | ------------ |
| `critical`  | Significant registration or overdue requirement issues  |
| `error`     | Requirement needs to be satisfied  |
| `warning`   | Number of credits required for next semester award  |
| `info`      | Print all requirement information  |
| `debug`     | Print debugging information when parsing PDF transcripts  |

## Examples

Print all information about students:
```
docker run -it -v `pwd`:/usr/src/app --rm --name grad-program grad-program --current-semester 'Fall 2020' --log-level info
```

Print the number of credits that the student needs next semester
```
docker run -it -v `pwd`:/usr/src/app --rm --name grad-program grad-program --current-semester 'Fall 2020' --log-level warning | egrep -v '(ERROR|CRITICAL)'
```

## Building Docker Image

To build the Docker image, run:
```
docker build -t grad-program .
```
