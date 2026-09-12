"""
Downloaders for the external sources listed in SIH26165_Data_Scarcity_Plan.md.

They must run on a machine with normal internet access (your laptop) - the
Cowork sandbox only reaches package registries.  Everything lands under
DATA/RAW/<source>/ and is then picked up by the CLEANING parsers.

    python -m CLEANING.fetch.fetch_all                 # everything
    python -m CLEANING.fetch.fetch_msha                # one source
    python -m CLEANING.fetch.fetch_iadc --max-pages 3  # smoke test

pip install requests beautifulsoup4 lxml   (already in CLEANING/requirements.txt)
"""
