# grad-program

`transcript.py` is a script for parsing the PDF advising transcripts produced by MySlice. The transcript data is parsed from the file `Transcripts.PDF` and a list of names and SUIDs are read from the file `Active Student Data.csv`

To build the Docker image:
```
docker build -t grad-program .
```

To run the parsing script:
```
docker run -it --rm --name grad-program grad-program --current-semester 'Fall 2020'
```

The optional argument `--log-level` can be used to print more or less
information. Valid levels are: `critical`, `error`, `warning`, and `info`
