
# MongoPersistence

Package to add persistence to your telegram bot in a mongodb database.

ATTENTION: MongoPersistence is a new project, it should work, but if you encounter any bugs please report them in the [Issues](https://github.com/LucaSforza/MongoPersistence/issues) section and if you have an idea how to fix it please consider opening a [PR](https://github.com/LucaSforza/MongoPersistence/pulls).
## Usage

First make sure you have created a database using mongodb.
If you haven't already, click [here](https://www.mongodb.com) to get started.

Then create a collection in your database for each type of data you want to make persistent.

```python
from mongopersistence import MongoPersistence
from telegram.ext import Application

mongodb = MongoPersistence(
    'your-mongodb-key',
    'your-database-name',
    name_col_user_data='my-collection-for-user-data'
)

application = Application.builder().token('your-token'
        ).persistence(mongodb
        ).build()
```

This code will only add persistence to user_data and since the `load_on_flush` attribute has not been specified, the data will be loaded continuously into the database even when the bot is running.

If you want the data not to be loaded continuously instead define:
```python
 MongoPersistence( ... ,load_on_flush=True,update_interval=60)
```

`update_interval` can also be undefined and the default is `60`.

One of the advantages of setting `load_on_flush = False` is that if you modify the database (either directly from the site or through the code of your other app) then it will automatically be updated to the modified data type inside your bot, without having to shut it down first !

If you want certain elements to be ignored and not saved in your database you could specify the keys to ignore in a list of the data type you want to ignore:

```python
from mongopersistence import MongoPersistence

mongodb = MongoPersistence(
	'your-mongodb-key',
	'your-database-name',
	name_col_user_data='my-collection-for-user-data',
  name_col_chat_data='my-collection-for-chat-data',
	ignore_general_data= ['cache'],
	ignore_user_data=['foo','bar']
)
```

The last thing to specify is to be CAREFUL in adding permission to your IP on the [mongodb site](https://www.mongodb.com), otherwise you will encounter an error running the bot.


## Installation

Install mongopersistence with pip

```bash
  pip install mongopersistence
```
    
## Roadmap

Search all the TODOs in this repo to see how you can contribute to this package, but in general:

- Add support for make persistent callback data.