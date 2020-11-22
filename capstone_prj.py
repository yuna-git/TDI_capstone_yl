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
import bokeh
from bokeh.models import Range1d, LinearAxis
from bokeh.plotting import figure, output_file, save, show
from bokeh.transform import dodge
from bokeh.models.tools import HoverTool

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
        return render_template('introduction.html')
    else:
        category = request.form['category']
        app.vars['category'] = category
        job_salary_num = dill.load(open('job_salary_num_1120.pkl', 'rb'))
        job_df = job_salary_num[job_salary_num['title']==category]
        df = job_df[job_salary_num['title']==category]
        df['sal'] = df['salary'].apply(lambda x: int(x.replace('$','').replace(',', '')))
        df2 = df.sort_values(by='job num', ascending=False)[:10]

        cities = df2.Loc.values
        output_file('./templates/job_top10.html', title="Top10 cities")
        ymin = int(df2['sal'].min())//1000*1000
        ymax = int(df2['sal'].max())//1000*1050
        p = figure(x_range=cities,y_range=(60000, ymax), plot_width=1200, plot_height=350, 
           title=('Top 10 cities with most job opportunities for ' + category),
           toolbar_location=None, tools='')
        p.vbar(x=dodge('Loc', -0.1, range=p.x_range), top='sal', width=0.2, source=df2, line_color = 'white', 
                legend_label="Salary", color='green')


        y2max = (int(df2['job num'].max())//100)*150
        p.extra_y_ranges = {'Job Number': Range1d(start=0, end=y2max)}
        p.add_layout(LinearAxis(y_range_name="Job Number"), 'right')
        p.vbar(x=dodge('Loc', 0.1, range=p.x_range), top='job num', width=0.2, source=df2, line_color = 'white', 
                legend_label="Job number", color='orange', y_range_name='Job Number')
        p.xgrid.grid_line_color = None
        p.legend.location = "top_right"
        p.legend.orientation = "horizontal"

        hover = HoverTool()
        hover.tooltips = [('Average salary', '@salary'), ('Job number', '@{job num}')]
        hover.mode = 'vline'
        p.add_tools(hover)
        save(p)
        return render_template('job_num_salary_plot.html', title=category)

@app.route('/job_num_salary_plot')
def plot_num_salary():
    return render_template('job_top10.html')


@app.route('/map_all', methods=['GET', 'POST'])
def map_all():
    if request.method == 'GET':
        return render_template('map_all.html')
    else:
#        if request.form['title'] =='':
#            category = 'Data Analytics'
#        else:
        category = request.form['category']
        app.vars['category'] = category
        living_cost_income = dill.load(open('living_cost_income_2019.pkl', 'rb'))
        job_salary_num = dill.load(open('job_salary_num_1120.pkl', 'rb'))
        job_df = job_salary_num[job_salary_num['title']==category]
        merge_df = pd.merge(living_cost_income, job_df, how='left', on='Loc')
#        print(merge_df.loc[2, 'title'])
# grab the number of opening position and salary for this job category
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
        merge_df['job num'].fillna(0, inplace=True)
        merge_df['salary'].fillna(0, inplace=True)
       
        merge_df['buying_power'] = merge_df['Average Income']/merge_df['Cost of Living Index']-50
        dill.dump(merge_df, open('temp_df.pkl', 'wb'))
        df = merge_df
        df['job_num_sq'] = df['job num'].apply(lambda x: x**0.2)

# plot the map html
        linear = cmp.LinearColormap(
#    ['yellow', 'green', 'purple'],
            ['blue', 'green', 'orange', 'red'],
            vmin=600, vmax=1000,
            caption='Normalized buying power' #Caption for Color scale or Legend
    )
        latitude = 37.0902
        longitude = -95.7129
        cost_income_map = folium.Map(location=[latitude, longitude], zoom_start=5)
       
        for lat, lon, buying_power, cost, income, city, job_salary, job_num, jobs_sq in zip(df['latitude'], df['longitude'], 
                                                         df['buying_power'], 
                                                         df['Cost of Living Index'], 
                                                         df['Average Income'], df['City'],
                                                         df['salary'], df['job num'],
                                                         df['job_num_sq']):
            folium.CircleMarker(
                [lat, lon],
                radius= 3*jobs_sq,
                popup = folium.Popup(html =('City: ' + str(city).capitalize() + '<br>'
                'Cost index level: ' + str(cost) +'%' +'<br>'
                'Average income: $' + str(int(income)//1000) +',' + str(int(income)%1000) + '<br>'
                'Average salary for ' + category + ': ' + job_salary + '<br>'
                'Opening positions: ' + str(job_num)
                ), max_width=150),
                color='b',
                key_on = buying_power,
                threshold_scale=[0,1,2,3],
                fill_color=linear(buying_power),
                fill=True,
                fill_opacity=0.7
                ).add_to(cost_income_map)
        linear.add_to(cost_income_map)
        cost_income_map.save(outfile = './templates/job_income_cost.html')
#        iframe = cost_income_map.get_root().render()
#        iframe = cost_income_map._repr_html_()
        return render_template('ds_job_map.html', job_category = category)


@app.route('/map')
def map():
    return render_template('job_income_cost.html')



@app.route('/summary', methods = ['POST'])
def compare_location():
#    dump()
    original_city = request.form['original']
    original = ' '.join( x.capitalize() for x in original_city.split())
    target_city = request.form['target']
    target = ' '.join( x.capitalize() for x in target_city.split())

    df = dill.load(open('temp_df.pkl', 'rb'))
    title = df.loc[3, 'title']
    original_income = df[df['City']==original]['Personal_income'].values[0]
    original_cost = df[df['City']==original]['Cost of Living Index'].values[0]
    original_bp = int(original_income/original_cost)
    original_salary = df[df['City']==original]['salary'].values[0]
    target_income = df[df['City']==target]['Personal_income'].values[0]
    target_cost = df[df['City']==target]['Cost of Living Index'].values[0]
    target_bp = int(target_income/target_cost)
    target_salary = df[df['City']==target]['salary'].values[0]

    income_ratio = (target_income - original_income)/original_income*100
    bp_ratio = (target_bp - original_bp)/original_bp*100

    original_income = '$' + str(int(original_income)//1000) + ',' + str(int(original_income)%1000)
    target_income = '$' + str(int(target_income)//1000) + ',' + str(int(target_income)%1000)
    if income_ratio > 0:
        income_ratio_change = 'increases ' + str(round(income_ratio, 2))+'%'
    else:
        income_ratio_change = 'decreases ' + str(round(income_ratio, 2))+'%'
    if bp_ratio > 0:
        bp_ratio_change = 'increases ' + str(round(bp_ratio, 2))+'%'
    else:
        bp_ratio_change = 'decreases ' + str(round(bp_ratio, 2))+'%'
    ori_sal = original_salary.replace(',', '').replace('$', '')
    target_sal = target_salary.replace(',', '').replace('$', '')
    salary_ratio = (int(target_sal) - int(ori_sal))/int(ori_sal)
    if  salary_ratio> 0:
        salary_change = 'increases ' + str(round(salary_ratio, 2))+'%'
    else:
        salary_change = 'decreases ' + str(round(salary_ratio, 2))+'%'

    return render_template('ds_job_map.html', original = original, target = target, original_income = original_income, original_cost = original_cost, target_income = target_income, target_cost = target_cost, income_ratio_change = income_ratio_change, bp_ratio_change = bp_ratio_change, title=title, original_salary = original_salary, target_salary=target_salary, salary_change = salary_change, job_category = title)



@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(debug=True)
