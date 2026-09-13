# verbatim — how to convert and check a batch

For research assistants. No programming needed.

## Once, on your machine

The README has the full step-by-step installation, with every click spelled out. In short:

1. Install Python from https://www.python.org/downloads/ — on Windows, tick
   **Add python.exe to PATH** on the first screen.
2. In Terminal (Mac) or Command Prompt (Windows), paste this whole line and
   press Enter:
   - Mac: `python3 -m pip install "verbatim[all] @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"`
   - Windows: `py -m pip install "verbatim[all] @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"`

   Do **not** run `pip install verbatim` on its own: that name belongs to an
   unrelated program, and you would get the wrong tool.
3. Only for **scanned** PDFs, install Tesseract — see the README.

If `verbatim` is "not found" afterwards, use `python3 -m verbatim` (Mac) or
`py -m verbatim` (Windows) instead.

## Every time

Type `verbatim` and press Enter. A window opens. Switch it to French with the
menu at the top right if you prefer; it remembers your choice.

### Convert

1. Choose the folder with the PDFs, and the folder for the TXT files.
2. Choose the output format: **COP decisions** or **Agreement texts**.
3. Press **Convert**.

The log tells you what happened to each file. When it finishes, it says how
many were converted and how many need checking.

### Check

The **Review** tab opens on the files that need attention, worst first. It works
on any folder of `.txt` files, including ones made by other tools: for those,
choose the folder holding the matching PDFs in **PDF folder** (same file names),
or tick **Text checks only (no PDF)**.

- ✗ means a problem was found. **!** means something is worth a look.
  ✓ means it was compared with its PDF and nothing was flagged. ○ means the
  text looks fine but has not been compared with its PDF yet. ☑ means you
  have already checked it.
- The list at the top says what to look at, and which page.
- Click one. The page appears on the left with the passage outlined, and the
  same passage is highlighted in the text on the right. **Compare just that
  paragraph** — you do not need to read the whole file.
- A **purple** background means those words were produced by a model rather
  than read from the PDF. Nothing in the document can confirm them, so check
  every one.
- Enter your name in **Checked by** (remembered for next time) and, if
  useful, a **Note**. Then press **Accept**, **Needs work** or **Reject**. It
  moves to the next file on its own.

For files verbatim converted, your decision is saved next to the file. For any
other file, the checks and your decision are saved **on your computer only** —
nothing is written into the folder, and colleagues do not see those decisions.

## What the messages mean

| Message | What it means |
| --- | --- |
| *N word(s) in the text do not appear in the PDF* | Words came out that are not in the source. The most serious finding: check them against the page. |
| *N word(s) in the PDF do not appear in the text* | Something was dropped. Sometimes legitimate (a removed header); check the page. |
| *N number(s) in the text do not appear in the PDF* | A number or date that is not in the source. Always check these. |
| *N page(s) were produced by a model* | Those pages were not read from the PDF but generated. Check every word. |
| *N word(s) look scrambled* | The PDF's own text is damaged, weaving two lines together. Usually needs re-converting with **Recognise text** set to *always*. |
| *the same N words repeat over and over* | The recogniser got stuck. Re-convert the file. |
| *the recogniser was only N% confident* | A poor scan. Read it carefully. |

## If something looks wrong

| Problem | Try |
| --- | --- |
| Two columns are mixed together | Set **Columns** to 2 |
| Everything is on one line per column when it should not be | Set **Columns** to 1 |
| A table came out as prose | Set **Tables** to *text* — only if the page is almost entirely table |
| A heading disappeared | Tick **keep headers/footers** |
| The text is garbled from the start | Set **Recognise text** to *always* |
| You need page numbers for citation | Tick **[page N] markers** |

If a scan is genuinely bad, ask David before using the Mistral option: it costs
money per page, and it is a model rather than a character reader, so everything
it produces has to be checked by hand.
