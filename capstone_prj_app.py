from flask import Flask, render_template, request, redirect
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import dill
import folium
import math
import geopy
from geopy.geocoders import Nominatim

app = Flask(__name__)
app.vars={}

def get_job_number(loc, job_title):
    params = {'q':job_title, 'l':loc, 'radius': 25}
    print(loc)
    print(job_title)
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
        return render_template('ds_job.html')
    else:
        category = request.form['title']
        app.vars['title'] = category
        living_cost_income = dill.load(open('living_cost_income.pkl', 'rb'))
        living_cost_income['job_opening'] = None

# grab the number of opening position for this job category
#        geolocator = Nominatim(user_agent="myapp")
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
        living_cost_income['buying_power_quartile'] = pd.qcut(living_cost_income['buying_power'], 4, labels=False)
        colordict = {0: 'blue', 1: 'green', 2: 'orange', 3: 'red'}
        df = living_cost_income
        df['job_num_sq'] = df['DE_opening'].apply(lambda x: x**0.15)


# plot the map html
        latitude = 37.0902
        longitude = -95.7129
        cost_income_map = folium.Map(location=[latitude, longitude], zoom_start=5)
        for lat, lon, buying_power_q, cost, income, city, de_jobs, jobs_sq in zip(df['latitude'], df['longitude'], 
                                                         df['buying_power_quartile'], 
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
                key_on = buying_power_q,
                threshold_scale=[0,1,2,3],
                fill_color=colordict[buying_power_q],
                fill=True,
                fill_opacity=0.7
                ).add_to(cost_income_map)
        cost_income_map.save(outfile = './templates/job_income_cost.html')

        return render_template('job_income_cost.html')




@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(debug=True)
