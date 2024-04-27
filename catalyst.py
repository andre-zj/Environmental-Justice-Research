import math
import pandas as pd
from sklearn.linear_model import LinearRegression  # I recently learned and cited this
from bokeh.plotting import figure, show
from bokeh.models import Label, ColumnDataSource, Scatter
from bokeh.layouts import gridplot

#Distance formula using latitude, longitude and converting to miles
def distance(s_lat, s_lon, d_lat, d_lon):
    earth_radius = 3959.0

    s_lat = s_lat * math.pi / 180.0
    s_lon = math.radians(s_lon)
    d_lat = math.radians(d_lat)
    d_lon = math.radians(d_lon)

    dist = math.sin((d_lat - s_lat) / 2) ** 2 + math.cos(s_lat) * math.cos(d_lat) * math.sin((d_lon - s_lon) / 2) ** 2

    return 2 * earth_radius * math.asin(math.sqrt(dist))

#Range function that specifies the amount to increment by
def drange(start, stop, step):
    while start < stop:
        yield start
        start += step

#Gathering median household income data from spreadsheet
zip_info = []
med_household_income = 84385
low_income_limit = 54300
income_database = pd.read_csv('zip_code_income_edit.csv')
zipincome_col = '$203,009 '#Column names (what it says in the first row of the desired columns)
zipcode2_col = '02468'
zip2lat_col = '42.32'
zip2lon_col = '-71.23'

#stores above information in a list of lists
for row in range(0, income_database.shape[0]):
    MA_zipcode2 = ['0' + str(income_database.at[row, zipcode2_col]).strip(' '),
                   income_database.at[row, zip2lat_col],
                   income_database.at[row, zip2lon_col],
                   int(income_database.at[row, zipincome_col].strip('$ ').replace(",", ""))]
    zip_info.append(MA_zipcode2)

#Gathering greenhouse gas emission data from spreadsheet
emission_limit = 10000
emission_sheet = pd.read_csv('ghgp_data_copy.csv')
emission_facility_id_col = '1005184'
emission_facility_name_col = 'ALYESKA PIPELINE SE/TAPS PUMP STATION 01'
emission_state_col = 'AK'
emission_lat_col = '70.26'
emission_lon_col = '-148.62'
emission_amount_col = '72699.974'

#turns desired spreadsheet data into a list of lists
MA_emission_sources = []
for index, row in emission_sheet.iterrows():
    if row[emission_state_col] == 'MA' and row[emission_amount_col] >= emission_limit:
        MA_emission_source = [
            row[emission_facility_id_col],
            row[emission_facility_name_col],
            row[emission_lat_col],
            row[emission_lon_col],
            row[emission_amount_col]
        ]
        MA_emission_sources.append(MA_emission_source)

#finds low income zipcodes
zipcodes_low_income = []
for zip in zip_info:
    if zip[3] < low_income_limit:
        zipcodes_low_income.append([zip[0], zip[3]])

#uses a for loops to determine which zip codes are within a certain distance from the radius
#stores values in a dictionary (values will repeat, as ones within 1 mile are also within 2)
radius = 0
radius_step = 0.5
radius_last = 5
zip_high_emissions = []
index = 0
for radius in drange(radius, radius_last, radius_step):
    radius = radius + radius_step
    for zipc in zip_info:#list of zipcode information
        index += 1
        total_emission = 0.0
        for item2 in MA_emission_sources:#list of emission sources
            d = distance(zipc[1], zipc[2], item2[2], item2[3])
            if d < radius:
                total_emission += item2[4]
        if total_emission > 0.0:
            dictionary = {
                'radius': radius,
                'zipcodes': zipc[0],
                'emissions': total_emission,
                'income': zipc[3],
                'latitudes': zipc[1],
                'longitudes': zipc[2]
            }
            zip_high_emissions.append(dictionary)

plots = []#List of plots

#makes a plot for each radius increment
for rad in drange(0.5, 5, 0.5):
    rad += 0.5
    # filtered_data = [x for x in zip_high_emissions if x[0] == rad]
    filtered_data = [x for x in zip_high_emissions if x['radius'] == rad]
    x_range = (0, 2500000)
    y_range = (0, 250000)


    #taking data from zip_high_emissions dictionary
    emissions = [x['emissions'] for x in filtered_data]
    income = [x['income'] for x in filtered_data]
    zipcodes = [x['zipcodes'] for x in filtered_data]
    latitudes = [x['latitudes'] for x in filtered_data]
    longitudes = [x['longitudes'] for x in filtered_data]
    colors = ['red' for x in filtered_data]

    #linear regression
    X_reshaped = [[val] for val in emissions]
    reg = LinearRegression()
    reg.fit(X_reshaped, income)
    y_pred = reg.predict(X_reshaped)

    #ColumnDataSource in bokeh
    data = ColumnDataSource(data=dict(
        zipcodes=zipcodes,
        income=income,
        emissions=emissions,
        latitudes=latitudes,
        longitudes=longitudes,
        colors=colors
    ))

    #tooltips for hover tool
    tooltips = [("Zip Code", "@zipcodes"), ("Median Income", "@income"), ("Total Emissions", "@emissions"),
                ("Latitude", "@latitudes"), ("Longitude", "@longitudes")]

    # Plot the data points and the regression line
    p = figure(x_range=x_range, y_range=y_range, title='Linear Regression for radius ' + str(rad),
               x_axis_label='total emissions', y_axis_label='median household income', tooltips=tooltips)
    for i in range(len(emissions)):
        if income[i] < low_income_limit:
            data.data["colors"][i]="red"
        else:
            data.data["colors"][i]="black"
    glyph = Scatter(x="emissions", y="income", size=5, line_color="colors", fill_color="colors")
    p.add_glyph(data, glyph)
    p.line(emissions, y_pred, line_width=2, color='red', legend_label=f'Linear Regression (Radius {rad})')
    
    #adds R^2 values and equations for emissions vs. income
    slope = reg.coef_[0]
    intercept = reg.intercept_
    r_squared = reg.score(X_reshaped, income)
    equation = f'y = {slope:.2f}x + {intercept:.2f}'
    r_squared_text = f'R-squared: {r_squared:.2f}'

    label_eq = Label(x=min(emissions), y=max(income), text=equation, text_color='green', text_font_size='10pt')
    label_rsquared = Label(x=min(emissions), y=max(income) - (max(income) - min(income)) * 0.1, text=r_squared_text,
                           text_color='green', text_font_size='10pt')

    p.add_layout(label_eq)
    p.add_layout(label_rsquared)

    #adds p to plot list
    plots.append(p)

    p.legend.location = 'bottom_right'

#makes a grid plot of all plots in list
grid = gridplot(plots, ncols=3)
show(grid)
