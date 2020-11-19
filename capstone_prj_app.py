from flask import Flask, render_template, request, redirect
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import dill
import folium
from folium.features import DivIcon
import math
import geopy
from geopy.geocoders import Nominatim
import branca
import branca.colormap as cmp

app = Flask(__name__)
app.vars={}

def get_job_number(loc, job_title):
    params = {'q':job_title, 'l':loc, 'radius': 25}
#    job_category = ''.join([x[0] for x in job_title.split()]) + '_jobs'
    response = requests.get('https://www.indeed.com/jobs', params = params)
    soup = BeautifulSoup(response.text, 'lxml')
#    jblist_loc = soup.select_one('div.resultsTop h1#jobsInLocation').text
    jblist_num = soup.select_one('div.resultsTop div#searchCountPages').text
    jobnum= jblist_num.split('of ')[1].split()[0]
    return int(''.join(jobnum.split(',')))


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('any_job.html')
    else:
        if request.form['title'] =='':
            category = 'Data Analytics'
        else:
            category = request.form['title']
        app.vars['title'] = category
        living_cost_income = dill.load(open('living_cost_income.pkl', 'rb'))
        living_cost_income['job_opening'] = None

# grab the number of opening position for this job category
        geolocator = Nominatim(user_agent="myapp")
#        for row in range(living_cost_income.shape[0]):
#             city = living_cost_income.loc[row,'City']
#             loc = living_cost_income.loc[row,'Loc']
#             geoloc = geolocator.geocode(city)
#             living_cost_income.loc[row, 'latitude'] = geoloc.latitude
#             living_cost_income.loc[row, 'longitude'] = geoloc.longitude
#             try : 
#                 living_cost_income.loc[row, 'job_opening'] = get_job_number(loc, category)
#             except AttributeError:
#                 living_cost_income.loc[row, 'job_opening'] = None
#        living_cost_income['job_opening'].fillna(0, inplace=True)
       
        living_cost_income['buying_power'] = living_cost_income['Personal_income']/living_cost_income['Cost of Living Index']
        df = living_cost_income
        df['job_num_sq'] = df['DE_opening'].apply(lambda x: x**0.15)


# plot the map html
        linear = cmp.LinearColormap(
#    ['yellow', 'green', 'purple'],
            ['blue', 'green', 'orange', 'red'],
            vmin=600, vmax=900,
            caption='Normalized buying power' #Caption for Color scale or Legend
)
        latitude = 37.0902
        longitude = -95.7129
        cost_income_map = folium.Map(location=[latitude, longitude], zoom_start=5)
        folium.map.Marker([51.0302, -85.2352],
                icon=DivIcon(
                    icon_size=(250,36),
                    icon_anchor=(0,0),
                    html='<div style="font-size: 10pt">The radius of marker indicates the number of current opening positions</div>',
        )
    ).add_to(cost_income_map)
        folium.map.Marker([28.0302, -128],
                icon=DivIcon(
                    icon_size=(250,36),
                    icon_anchor=(0,0),
#                    html='<div style="font-size: 11pt">The radius of marker indicates the number of current opening positions</div>',
                    html = "<form id='select location' method='post' action='/location'> <p> Please enter the orignal location and target location: </p> <p> Orignal location: <input type = 'text' name ='original' /></p> <p> Target locaitoin: <input type = 'text' name = 'target' /> </p> <p> <input type='submit' value = 'Submit'> </p> </form>"
        )
    ).add_to(cost_income_map)
        for lat, lon, buying_power, cost, income, city, de_jobs, jobs_sq in zip(df['latitude'], df['longitude'], 
                                                         df['buying_power'], 
                                                         df['Cost of Living Index'], 
                                                         df['Personal_income'], df['City'],
                                                         df['DE_opening'],
                                                         df['job_num_sq']):
            folium.CircleMarker(
                [lat, lon],
                radius= 3*jobs_sq,
                popup = ('City: ' + str(city).capitalize() + '<br>'
                 'Personal_income: $' + str(int(income)) + '<br>'
                 'cost index level: ' + str(cost) +'%' +'<br>'
                 'opening positions: ' + str(de_jobs)
                ),
                color='b',
                key_on = buying_power,
                threshold_scale=[0,1,2,3],
                fill_color=linear(buying_power),
                fill=True,
                fill_opacity=0.7
                ).add_to(cost_income_map)
        linear.add_to(cost_income_map)
        cost_income_map.save(outfile = './templates/job_income_cost.html')

        return render_template('job_income_cost.html')



@app.route('/location', methods = ['GET'])
def compare_location():
    original = request.form['original'].capitalize()
    target = request.form['target'].capitalize()

    df = dill.load(open('living_cost_income.pkl', 'rb'))
    original_income = df[df['City']==original]['Personal_income'].values[0]
    original_cost = df[df['City']==original]['Cost of Living Index'].values[0]
    original_bp = int(original_income/original_cost)
    target_income = df[df['City']==target]['Personal_income'].values[0]
    target_cost = df[df['City']==target]['Cost of Living Index'].values[0]
    target_bp = int(target_income/target_cost)
    income_ratio = round((target_income - original_income)/original_income, 3)*100
    bp_ratio = round((target_bp - original_bp)/original_bp, 3)*100


    return render_template('summary.html', original = original, target = target, original_income = int(round(original_income/100)*100), original_cost = original_cost, target_income = int(round(target_income/100)*100), target_cost = target_cost, income_ratio = (str(income_ratio)+'%'), bp_ratio = (str(bp_ratio)+'%'))



@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(debug=True)
