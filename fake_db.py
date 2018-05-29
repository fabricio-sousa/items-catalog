from database_setup import *
from sqlalchemy import create_engine
import datetime
from sqlalchemy.orm import sessionmaker, scoped_session

engine = create_engine('sqlite:///catalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine
DBSession = scoped_session(sessionmaker(bind=engine))
session = DBSession()


# Create dummy users
User1 = User(name="Fabricio Sousa", email="fraterincognito1@gmail.com",
             picture='https://i.imgur.com/v9Ck7Eo.jpg')
session.add(User1)
session.commit()

User2 = User(name="Fabricio Sousa", email="fraterincognito2@gmail.com",
             picture='https://i.imgur.com/v9Ck7Eo.jpg')
session.add(User2)
session.commit()

User3 = User(name="Fabricio Sousa", email="themysticwalker@gmail.com",
             picture='https://i.imgur.com/v9Ck7Eo.jpg')
session.add(User3)
session.commit()

User4 = User(name="Fabricio Sousa", email="fsousa@sageoutsource.commit",
             picture='https://i.imgur.com/v9Ck7Eo.jpg')
session.add(User4)
session.commit()


# Create fake categories
Category1 = Category(name="Cats",
                      user_id=1)
session.add(Category1)
session.commit()

Category2 = Category(name="Dogs",
                      user_id=2)
session.add(Category2)
session.commit()

Category3 = Category(name="Lizards",
                      user_id=3)
session.add(Category3)
session.commit()

Category4 = Category(name="Computers",
                      user_id=4)
session.add(Category4)
session.commit()


# Create fake category items
Item1 = Items(name="Emily",
               date=datetime.datetime.now(),
               description="An annoying little fat cat.",
               picture_url="https://i.imgur.com/cZjvh7W.jpg",
               category_id=1,
               user_id=1)
session.add(Item1)
session.commit()

Item2 = Items(name="Emerson",
               date=datetime.datetime.now(),
               description="A playful, energetic dog.",
               picture_url="https://i.imgur.com/kQxLcXF.jpg",
               category_id=2,
               user_id=2)
session.add(Item2)
session.commit()


Item3 = Items(name="Ziggy",
               date=datetime.datetime.now(),
               description="Rest in peace.",
               picture_url="https://i.imgur.com/nLA6OiF.jpg",
               category_id=3,
               user_id=3)
session.add(Item3)
session.commit()

Item4 = Items(name="Alienware R17",
               date=datetime.datetime.now(),
               description="My dev and gaming laptop.",
               picture_url="https://i.imgur.com/Ke86cDn.jpg",
               category_id=4,
               user_id=4)
session.add(Item4)
session.commit()


print "Database populated."
