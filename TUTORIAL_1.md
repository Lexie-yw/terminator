# Terminator Tutorial Part 1

Terminator is an open source terminology management platform built with Django and Python. 

## Download and Install Prerequisites

Download and install [Visual Studio](https://visualstudio.microsoft.com/downloads/)

The latest Community version is fine.

Make sure you install the ASP.NET workload for web development.

![](screenshots/ASP.NET.png)

Download and install [Python](https://www.python.org/downloads/). Make sure you check the box "Add Python 3.x to PATH."

Download and install [XAMPP](https://www.apachefriends.org/download.html).

Download and install [MySQL](https://dev.mysql.com/downloads/installer/).

Use the default settings when configuring Type and Networking.

![](screenshots/MySQL_1.png)

## Configure Python environment

Install virtualenv and virtualenvwrapper.

If on mac, open the Terminal and type the following:

```python
pip install virtualenv
pip install virtualenvwrapper
```

If on Windows, open the command line and type the following:

```
pip install virtualenv
pip install virtualenvwrapper-win
```

In the command line, enter the following commands:

```
mkvirtualenv myTB
git clone https://github.com/nicklambson/terminator.git
cd terminator
pip install -r requirements/base.txt
pip install mysqlclient
```

Remember! All commands should be executed inside the virtual environment! If you close the command line, remember to re-enter the virtual environment by entering this code:

```
workon myTB
```

## Start Apache and MySQL

Open XAMPP.

Start Apache, then start MySQL.

XAMPP should look like this after starting Apache and MySQL.

![](screenshots/XAMPP.png)

## Create a Database

Open MySQL Command Line Client.

Enter your password.

If successful, you will see a screen like this.

![](screenshots/MySQL_CLI.png)

Enter the following to show existing databases:

```
show databases;
```

Enter the following to create a new Term Base (TB):

```
CREATE DATABASE myTB;
```

Verify that the database was created by viewing the databases again:

```
show databases;
```

## Modify Settings

Create a copy of the settings.py file in the project folder, and rename it to local_settings.py.

Open local_settings.py.

In DATABASES, match the following settings:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'myTB',
        'USER': 'root',
        'PASSWORD': '',
        'HOST' : '',
        'PORT' : '3306',
        'OPTIONS': {'init_command': 'SET storage_engine=INNODB',}
    }
}
```

Important: comment out lines 201 to the end of the local_settings.py file.

![](screenshots/local_settings.png)

## Migrate Data Structure

Navigate to the project folder inside terminator:

```
cd project
```

Populate your myTB database with structure and data from Terminator:

```
python manage.py migrate --noinput
```

If successful, you should see a screen like this:

![](screenshots/migrated.png)

## Create a Superuser

For the purposes of this exercise, we will create a Django superuser from the command line:

```
python manage.py createsuperuser --username=joe --email=joe@example.com
```

You will be prompted for a password. After you enter a password, the superuser will be created immediately.

## Run the Server

To run the server, enter this line in the command line:

```
python manage.py runserver
```

Access the server in your web browser at [http://localhost:8000/](http://localhost:8000/).

Terminator is now running.

Log in with the credentials of the superuser you just created:

![](screenshots/log_in.png)

Add /admin/ to the url to go to the Terminator administration page.

```
http://localhost:8000/admin/
```

Configure your term base according to your preference.