from tethys_sdk.gizmos import DatePicker, MapView, MVLayer, MVView, TextInput, Button, ButtonGroup, LinePlot, ScatterPlot, ToggleSwitch, RangeSlider, TimeSeries, PlotView, SelectInput
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .model import recessionExtract, createAbJson
import pandas as pd
import numpy as np
from .app import RecessionAnalyzer
import os
import cPickle as pickle

import simplejson as json

import urllib
from io import StringIO


@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    gages_initial               = ['11476500','11477000']
    start_initial               = '2000-01-01'
    stop_initial                = '2015-01-01'
    concave_initial             = False
    nonlinear_fitting_initial   = False
    rec_sense_initial           = 1
    min_length_initial          = 4
    antecedent_moisture_initial = 1
    lag_start_initial           = 0
    select_gage_options_initial = ''
    select_gage_options_tuple   = []
    abJson                      = ''
    scatter_plot_view           = buildRecParamPlot([])
    line_plot_view              = buildFlowTimeSeriesPlot([])
    submitted                   = False


    ## sites = pd.read_csv('/usr/lib/tethys/src/tethys_apps/tethysapp/my_first_app/public/huc_18.tsv',sep='\t',header=30,index_col=False,skiprows=[31])
    ## sites = sites[sites.site_tp_cd == 'ST']
    ## names = sites.station_nm

    ## values = [str(x) for x in list(sites.site_no)]
    ## text = [num + ' ' + name[0:20] for (num,name) in zip(values,names)]
    ## gages_options_options = zip(text,values)
    ## gages_options_options_dict = dict(zip(values,text))

    # "Analyze recessions" button has been pressed
    # this stores new set of analysis parameters
    # and performs recession analysis, stores data in dictionaries
    # creates a new dropdown box with user gages
    if request.POST and 'analyze' in request.POST:
        #### PRESERVE THE PREVIOUS STATE ######
        gages_initial   = request.POST.getlist("gages_input")
        # start_initial   = request.POST['start_input']
        # stop_initial    = request.POST['stop_input']
          
        print('\n\n\n\n\n')
        print(gages_initial)
        print(type(gages_initial))
        
        if 'concave_input' in request.POST: concave_initial=True;
        else: concave_initial=False;
        
        if 'nonlinear_fitting_input' in request.POST: nonlinear_fitting_initial=True 
        else: nonlinear_fitting_initial=False
        
        rec_sense_initial   = request.POST['rec_sense_input']
        min_length_initial  = request.POST['min_length_input']
        lag_start_initial   = request.POST['lag_start_input']
        
        antecedent_moisture_initial = request.POST['antecedent_moisture_input']    
        ########################################
        
        
        
        app_workspace = RecessionAnalyzer.get_user_workspace(request.user)
        new_file_path = os.path.join(app_workspace.path,'current_plot.txt')
        pickle.dump(request.POST, open(new_file_path[:-4] + '.p','w'))
        post = pickle.load(open(new_file_path[:-4] + '.p','r'))
        
        submitted   = True
        ## gageNames   = post.getlist("gages_input")
        gageNames   = ['11476500','11477000']
        start       = '2000-01-01'
        ## start        = post['start_input']
        stop        = '2015-01-01'
        ## stop         = post['stop_input']
        rec_sense   = post['rec_sense_input']
        min_length  = post['min_length_input']
        ante_moist  = post['antecedent_moisture_input']
        lag_start   = post['lag_start_input']

        nonlin_fit  = post.get('nonlinear_fitting_input',False)
        concave     = post.get('concave_input', False)

        min_length  = float(min_length)
        selectivity = float(rec_sense)*500

        sitesDict, startStopDict = recessionExtract(gageNames,start,stop,ante=10,alph=0.90,window=3,selectivity=selectivity,minLen=min_length,option=1,nonlin_fit=nonlin_fit)

        abJson = createAbJson(sitesDict,gageNames);


        new_file_path = os.path.join(app_workspace.path,'current_dict.p')
        pickle.dump(sitesDict, open(new_file_path,'w'))

        new_file_path = os.path.join(app_workspace.path,'current_startStop.p')
        pickle.dump(startStopDict, open(new_file_path,'w'))

        gageName    = gageNames[0]
        ts          = sitesDict[gageName]
        startStop   = startStopDict[gageName]
        startVec    = startStop[0]
        endVec      = startStop[1]
        flow        = ts[gageName];
        tsinds      = ts.index
        data        = zip(tsinds,flow);


        series = [];

        series.append({'name':' ','color':'#0066ff',
                           'data':zip(flow[tsinds[0]:startVec[0]].index,flow[tsinds[0]:startVec[0]])})
        series.append({'name':' ','color':'#ff6600',
                           'data':zip(flow[startVec[0]:endVec[0]].index,flow[startVec[0]:endVec[0]])})
        for i in np.arange(0,len(startVec)-1):
            series.append({'name':' ','color':'#0066ff',
                           'data':zip(flow[endVec[i]:startVec[i+1]].index,flow[endVec[i]:startVec[i+1]])})
            series.append({'name':' ','color':'#ff6600',
                           'data':zip(flow[startVec[i+1]:endVec[i+1]].index,flow[startVec[i+1]:endVec[i+1]])})

        series.append({'name':' ','color':'#0066ff',
                           'data':zip(flow[endVec[-1]:tsinds[-1]].index,flow[endVec[-1]:tsinds[-1]])})
                           
        ## select_gage_options_tuple   = [(gages_options_options_dict[x],x) for x in gageNames]
        ## select_gage_options_initial = gages_options_options_dict[gageNames[0]]
        
        line_plot_view              = buildFlowTimeSeriesPlot(series)

        avals               = ts['A0n'][ts['A0n'] > 0 ].values;
        bvals               = ts['Bn'][ts['Bn']>0].values;
        tuplelist           = zip(avals,bvals)
        scatter_plot_view   = buildRecParamPlot(tuplelist)
        

    #if submitting a new site with the dropdown menu
    #should also persist the data, but use the
    #stored post from the initial submit
    if request.POST and 'update' in request.POST:
        app_workspace = RecessionAnalyzer.get_user_workspace(request.user)
        new_file_path = os.path.join(app_workspace.path,'current_plot.txt')
        post = pickle.load(open(new_file_path[:-4] + '.p','r'))
        
        gages_initial       = ['11476500','11477000']
        # gages_initial       = post.getlist("gages_input")
        # start_initial       = post['start_input']
        # stop_initial        = post['stop_input']
        rec_sense_initial   = post['rec_sense_input']
        min_length_initial  = post['min_length_input']
        ante_moist_initial  = post['antecedent_moisture_input']
        lag_start_initial   = post['lag_start_input']
        nonlin_fit_initial  = post.get('nonlinear_fitting_input',False)
        concave_initial     = post.get('concave_input', False)
        
        new_file_path = os.path.join(app_workspace.path,'current_dict.p')
        sitesDict = pickle.load(open(new_file_path,'r'))

        new_file_path = os.path.join(app_workspace.path,'current_startStop.p')
        startStopDict = pickle.load(open(new_file_path,'r'))

        submitted   = True

        gageName    = ['11476500','11477000']
        ## gageName    = request.POST['gage_input']
        gageNames   = ['11476500',"11477000"]
        ## gageNames   = request.POST.getlist("gages_input")

        ts          = sitesDict[gageName]
        startStop   = startStopDict[gageName]
        startVec    = startStop[0]
        endVec      = startStop[1]
        flow        = ts[gageName];
        tsinds      = ts.index
        data        = zip(tsinds,flow);
        series      = [];

        series.append({'name':' ','color':'#0066ff',
                           'data':zip(flow[tsinds[0]:startVec[0]].index,flow[tsinds[0]:startVec[0]])})
        series.append({'name':' ','color':'#ff6600',
                           'data':zip(flow[startVec[0]:endVec[0]].index,flow[startVec[0]:endVec[0]])})
        for i in np.arange(0,len(startVec)-1):
            series.append({'name':' ','color':'#0066ff',
                           'data':zip(flow[endVec[i]:startVec[i+1]].index,flow[endVec[i]:startVec[i+1]])})
            series.append({'name':' ','color':'#ff6600',
                           'data':zip(flow[startVec[i+1]:endVec[i+1]].index,flow[startVec[i+1]:endVec[i+1]])})

        series.append({'name':' ','color':'#0066ff',
                           'data':zip(flow[endVec[-1]:tsinds[-1]].index,flow[endVec[-1]:tsinds[-1]])})

        ## select_gage_options_tuple   = [(gages_options_options_dict[x],x) for x in gageNames]
        ## select_gage_options_initial = gages_options_options_dict[gageNames[0]]
        

        
        
        line_plot_view              = buildFlowTimeSeriesPlot(series)

        avals               = ts['A0n'][ts['A0n'] > 0 ].values;
        bvals               = ts['Bn'][ts['Bn']>0].values;
        tuplelist           = zip(avals,bvals)
        scatter_plot_view   = buildRecParamPlot(tuplelist)
    

    ## gages_options = SelectInput(display_text='Select gage(s)',
    ##                        name='gages_input',
    ##                        multiple=True,
    ##                        # options=gages_options_options,
    ##                        options=['11476500','11477000'],
    ##                        initial=['11476500','11477000'])
    ##                        # initial=[gages_options_options_dict[init] for init in gages_initial])
                            
    ## start_options = DatePicker(name='start_input',
    ##                                         display_text='Start date',
    ##                                         autoclose=True,
    ##                                         format='yyyy-m-d',
    ##                                         start_date='01/01/1910',
    ##                                         initial=start_initial)
                                            
    ## stop_options = DatePicker(name='stop_input',
    ##                                         display_text='Stop date',
    ##                                         autoclose=True,
    ##                                         format='yyyy-m-d',
    ##                                         start_date='01/01/1910',
    ##                                         initial=stop_initial)

    concave_options = ToggleSwitch(name='concave_input', size='small', initial=concave_initial, display_text='Concave recessions')

    nonlinear_fitting_options = ToggleSwitch(name='nonlinear_fitting_input', display_text='Nonlinear fitting',size='small',initial = nonlinear_fitting_initial)
    
    min_length_options = RangeSlider(name='min_length_input', min=4, max=10, initial=min_length_initial, step=1,attributes={"onchange":"showValue(this.value,'min_length_initial');"})
    
    rec_sense_options = RangeSlider(name='rec_sense_input', min=0, max=1, initial=rec_sense_initial, step=0.01,
                           attributes={"onchange":"showValue(this.value,'rec_sense_initial');"})

    antecedent_moisture_options = RangeSlider(name='antecedent_moisture_input', min=0, max=1, initial=antecedent_moisture_initial, step=0.01,attributes={"onchange":"showValue(this.value,'antecedent_moisture_initial');"})

    lag_start_options = RangeSlider(name='lag_start_input', min=0, max=3, initial=lag_start_initial, step=1,attributes={"onchange":"showValue(this.value,'lag_start_initial');"})

    select_gage_options = SelectInput(display_text='Select gage',
                       name='gage_input',
                       multiple=False,
                       initial=select_gage_options_initial,
                       options=select_gage_options_tuple,
                       attributes={"onchange":"updatePlot(this.value);"})

    context = { #'start_options': start_options,
                'rec_sense_initial':rec_sense_initial,
                'antecedent_moisture_initial':antecedent_moisture_initial,
                'lag_start_initial':lag_start_initial,
                'min_length_initial':min_length_initial,
                #'stop_options':stop_options,
                #'gages_options' : gages_options,
                'concave_options': concave_options,
                'nonlinear_fitting_options':nonlinear_fitting_options,
                'min_length_options':min_length_options,
                'submitted':submitted,
                'antecedent_moisture_options':antecedent_moisture_options,
                'lag_start_options':lag_start_options,
                'rec_sense_options':rec_sense_options,
                'line_plot_view':line_plot_view,
                'scatter_plot_view':scatter_plot_view,
                'select_gage_options':select_gage_options,
                'abJson':abJson}

    return render(request, 'recession_analyzer/home.html', context)


def buildFlowTimeSeriesPlot(series):
    highcharts_object = {
        'chart': {
            'zoomType': 'x'
        },
        'title': {
            'text': 'Flow time series'
        },
        'legend': {
            'layout': 'vertical',
            'align': 'right',
            'verticalAlign': 'middle',
            'borderWidth': 0,
            'enabled': False
        },
        'xAxis': {
            'title': {
                'enabled': True,
                'text': 'time',
                'offset': 35
            },
            'type': 'datetime',
            'tickLength': 10
        },
        'yAxis': {
            'title': {
                'enabled': True,
                'text': 'Discharge [cfs]'
            }
        },
        'tooltip': {
            'pointFormat': '{point.y} cfs',
            'valueDecimals': 2,
            'xDateFormat': '%d %b %Y %H:%M'
        },
        'series': series}
    return PlotView(highcharts_object=highcharts_object,
                              width='100%',
                              height='300px',
                              attributes='id=hydrograph-plot')

def buildRecParamPlot(tuplelist):
    scatter_highchart = {
        'chart': {
            'type':'scatter',
            'zoomType': 'xy'
        },
        'title': {
            'text': 'Recession parameters'
        },
        'legend': {
            'layout': 'vertical',
            'align': 'right',
            'verticalAlign': 'middle',
            'borderWidth': 0,
            'enabled': False
        },
        'exporting': {
            'enabled':'true'
        },
        'tooltip': {
            'pointFormat':'b={point.y:,.2f}, a={point.x:,.2f}'
        },
        'xAxis': {
            'title': {
                'enabled': True,
                'text': 'a',
                'offset': 35
            },
            'type': 'logarithmic',
            'tickLength': 10
        },
        'yAxis': {
            'title': {
                'enabled': True,
                'text': 'b'
            }
        },
        'series': [{'name':' ','data':tuplelist}]}

    return PlotView(highcharts_object=scatter_highchart,
                              width='100%',
                              height='300px',
                              attributes='id=ab-scatter')
