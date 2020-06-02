# Polyphony
A more robust implementation of PluralKit that hooks into the PluralKit API

# How to Run
Create a `.env` file in the project root to set your environment variables. Polyphony takes all of it's configuration in the form of environment variables.

- `DEBUG` - Python Boolean, Activates Debug Mode
- `TOKEN` - Discord Bot Token
- `DATABASE_URI` - Location of the SQLite database ([See more info here](https://docs.python.org/3/library/sqlite3.html))
- `MESSAGE_CACHE_SIZE` - How many recent messages are stored in memory for each instance (only message IDs are stored) <!--TODO: The API contains a message cache already so this may be deprecated-->
- `MODERATOR_ROLES` - List of role names (default: "Moderator")

This project was built on Python 3.8.2.

Dependency, testing, and build management is done using [Poetry](https://python-poetry.org/). Install Poetry on your system and then run `poetry install` in the project root.

> Pipenv will be deprecated

To run polyphony, use `poetry run polyphony`.

# Contributing
Do it right the first time and follow these guidelines.

## Style Guide
- Code is formatted using Black.
- All modules, functions, and classes contain a docstring conforming to Sphinx conventions
- Readability > Efficiency
- Use camel case for class names and underscores for everything else

## Questions
Ping a mod or open a ticket on The Valley discord server

## Reporting Issues
- Describe what you expected to happen
- If possible, include reproducible examples
- Describe what actually happened (including logging messages and traceback)
- Double check your packages are the same as what is defined in the Pipfile

## Submitting Patches
- Use Black to format your code
- Clearly list/explain what your patch adds/updates (include issue number if relevant)
