# # import sqlite3
# # import pandas as pd
# #
# # con = sqlite3.connect('products.db')
# # cur = con.cursor()
# #
# # con.commit()
# # con.close()
#
#
# from geopy.geocoders import Nominatim
#
# # Initialize geocoder
# geolocator = Nominatim(user_agent="city_finder")
# def verify_city(city):
#     try:
#         print(geolocator.geocode(city,timeout=10))
#         return True
#     except:
#         return False
# print(verify_city('Baku'))
# #
# #
# # def get_coordinates(city_name):
# #     try:
# #         location = geolocator.geocode(city_name, timeout=10)
# #         if location:
# #             return [location.latitude, location.longitude]
# #         return None
# #     except:
# #         return None
# #
# # print(get_coordinates('New York'))
#
import sqlite3

con = sqlite3.connect("products.db")

for row in con.execute(
    "SELECT name FROM sqlite_master WHERE type='index';"
):
    print(row)

con.close()