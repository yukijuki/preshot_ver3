***Preshot_ver3 setup***

*install prerequisites*
$ brew install python3
$ brew install git
Install PostgreSQL somehow (desktop apps work great for testing), then:
$ psql
# create database preshot;
# \q
if you cannot login to psql by default, find pg_hba.conf then set methods for all to trust

*get git repository*
$ cd ~/
$ git clone https://github.com/yukijuki/preshot_ver3.git
$ cd preshot_ver3

*make a venv and install the requirements.txt*
$ python3 -m venv venv
$ source venv/bin/activate
$ pip3 install -r requirements.txt

*set up SQLAlchemy migrations for PostgreSQL*
To prevent weird "but it works on my machine" issues,
we should be "working from scratch" each time for migrations on MASTER.
$ flask db init
$ flask db migrate -m "Initial migration."
$ flask db upgrade