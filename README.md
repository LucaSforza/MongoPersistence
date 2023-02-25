
# MongoPersistence

Package to add persistence to your telegram bot in a mongodb database.

ATTENTION: MongoPersistence is a new project, it should work, but if you encounter any bugs please report them in the [Issues](https://github.com/LucaSforza/MongoPersistence/issues) section and if you have an idea how to fix it please consider opening a [PR](https://github.com/LucaSforza/MongoPersistence/pulls).
## Usage

First make sure you have created a database using mongodb.
If you haven't already, click [here](https://www.mongodb.com) to get started.

Then create a collection in your database for each type of data you want to make persistent.

```python
from mongopersistence import *
from telegram.ext import Application

dbhelper = DBMongoHelper(
    'your-mongodb-key',
    'your-database-name',
    name_col_user_data='my-collection-for-user-data'
)

application = Application.builder().token('your-token'
        ).persistence(MongoPersistence(dbhelper)
        ).build()
```

With this code you will add persistence only to user_data and since the `load_on_flush` attribute has not been specified then the data will be loaded only when the bot is shut down.

If you want the data to be loaded continuously instead define:
```python
 MongoPersistence(dbhelper,load_on_flush=False,update_interval=60)
```

`update_interval` can also be undefined and the default is `60`.

One of the advantages of setting `load_on_flush = False` is that if you modify the database (either directly from the site or through the code of your other app) then it will automatically be updated to the modified data type inside your bot, without having to shut it down first !

The last thing to specify is to be CAREFUL in adding permission to your IP on the [mongodb site](https://www.mongodb.com), otherwise you will encounter an error running the bot.


## Installation

Install mongopersistence with pip

```bash
  pip install mongopersistence
```
    
## Roadmap

Search all the TODOs in this repo to see how you can contribute to this package, but in general:

- Add support for make persistent callback data.

- Add a feature that allows you to ignore dictionary elements using string lists so they don't become persistent.

