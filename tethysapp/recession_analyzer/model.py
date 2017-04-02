# Put your persistent store models in this file
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float
from sqlalchemy.orm import sessionmaker
from .app import RecessionAnalyzer
import os
import cPickle as pickle
import simplejson as json
from django import template
from django.utils.safestring import mark_safe
from lxml import etree

import pandas as pd
import time
import numpy as np
import urllib
from io import StringIO
from numpy import NaN, Inf, arange, isscalar, asarray, array
import sys
from scipy import stats as sp
from scipy import optimize as op
import time


def recessionExtract(gageName, start, stop, ante=10, alph=0.90, window=3,
                     selectivity=100, minLen=5, option=1, nonlin_fit=False):
    sitesDict = {}
    startStopDict = {}
    for site in gageName:
        d = getTimeSeries()
        dateandtime = pd.to_datetime(d['Time'])
        d = pd.DataFrame(d['Discharge'].values, columns=[site], index=pd.DatetimeIndex(dateandtime))
        selector = (d[site].max() - d[site].min()) / selectivity
        [maxtab, mintab] = peakdet(d[site], selector)

        # Initialize peaks
        d['peaks'] = -1

        # Get rid of peaks too close to the start

        if ante>2:
            maxtab = maxtab[maxtab[:, 0].astype(int) > ante]
        else:
            maxtab = maxtab[maxtab[:, 0].astype(int) > 1]

        d.ix[maxtab[:, 0].astype(int), 'peaks'] = maxtab[:, 1]

        d['smooth'] = pd.rolling_mean(d[site], window)
        d['smooth'][0:2] = d[site][0:2]
        d['Dunsmooth'] = d[site].diff().shift(-1)
        d['DDsmooth'] = d['smooth'].diff().shift(-1).diff().shift(-1)
        d['DDunsmooth'] = d[site].diff().shift(-1).diff().shift(-1)

        # Get rid of nans at end
        d = d[:-2]

        # Boolean vector for recession periods
        if option == 0:
            d['choose'] = d['Dunsmooth'] < 0
        else:
            d['choose'] = (d['Dunsmooth'] < 0) & ((d['DDsmooth'] >= 0) | (d['DDunsmooth'] >= 0))

        # Each peak should have associated with it an API, an An, A0n, Bn, A, A0, B
        # an rsqn, and an rsq. Loop through all peaks, compute each parameter

        datesMax = d.ix[d['peaks'] > 0].index
        startVec = np.array([])
        endVec = np.array([])
        bfitVec = np.array([])
        afitVec = np.array([])
        apiVec=np.array([])
        d['An'] = np.nan
        d['Bn'] = np.nan
        d['A0n'] = np.nan
        d['api'] = np.nan
        d['qn'] = np.nan

        for i in np.arange(len(datesMax) - 1):
            recStart = datesMax[i]
            peak2 = datesMax[i + 1]
            recEnd = d[recStart:peak2][d[recStart:peak2]['choose'] == False].index[0]
            if len(d[recStart:recEnd]) < minLen:
                continue

            t = np.arange(len(d[site][recStart:recEnd]))
            q0 = d[site][recStart]
            if not nonlin_fit:
                ab = fitRecession(t, d[site][recStart:recEnd])
                afit = ab[0]
                bfit = ab[1]
                if bfit >= 1 and bfit < 10 and afit > 0:
                    afitVec = np.append(afitVec, afit)
                    bfitVec = np.append(bfitVec, bfit)
                    startVec = np.append(startVec, recStart)
                    endVec = np.append(endVec, recEnd)
                    #d['An'][recStart] = afit; d['Bn'][recStart]=bfit;
                    beforeRec = d[site][recStart-pd.DateOffset(days=ante):recStart].values
                    factor = alph**np.arange(len(beforeRec))[::-1]
                    api = np.sum(beforeRec*factor)
                    apiVec = np.append(apiVec, api)
            else:
                def func(t, a, r):
                    return (q0**(r)-a*r*t)**(1/r)
                try:
                    #ab=fitRecession(t,d[site][recStart:recEnd])
                    #popt, cov = op.curve_fit(func,t,d[site][recStart:recEnd],p0=[ab[0],1-ab[1]]); 
                    # these initial guesses mirror Dralle's Matlab implementation
                    popt, cov = op.curve_fit(func, t, d[site][recStart:recEnd], p0=[0.01, -0.5], maxfev=1000);
                except RuntimeError:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print('RuntimeError!')
                    print(exc_value)
                    continue
                afit = popt[0]
                bfit = 1 - popt[1]
                if bfit >= 1 and bfit < 10:
                    afitVec = np.append(afitVec, afit)
                    bfitVec = np.append(bfitVec, bfit)
                    startVec = np.append(startVec, recStart)
                    endVec = np.append(endVec, recEnd)
                    beforeRec = d[site][recStart-pd.DateOffset(days=ante):recStart].values
                    factor = alph**np.arange(len(beforeRec))[::-1]
                    api = np.sum(beforeRec*factor)
                    apiVec = np.append(apiVec, api)

        ## DRALLE: SHOULD WE SPLIT THIS INTO TWO DICTIONARIES? ONE FOR THE TIME SERIES STUFF
        ## AND ANOTHER FOR THE RECESSION PARAMETERS STUFF?
        a0vec, q0vec = BergnerZouhar(afitVec, bfitVec)
        d['An'].loc[startVec] = afitVec
        d['Bn'].loc[startVec] = bfitVec
        d['api'].loc[startVec] = apiVec
        d['A0n'].loc[startVec] = a0vec
        d['qn'].loc[startVec] = q0vec
        sitesDict[site] = d

        startStopDict[site] = (startVec, endVec)

    return sitesDict, startStopDict


def fitRecession(time, discharge):
    """ INPUTS: time [numpy array]
                discharge [numpy array]
    
        OUTPUTS: recession parameter (a,b) pair
    
        This is a very simple fitting procedure, but it can easily be superceded.
    """
    dq = np.diff(discharge)
    logdq = np.log(-dq)

    p = np.polyfit(np.log(discharge[1:]), logdq, 1)
    return np.exp(p[1]), p[0]   # (a,b)


def BergnerZouhar(A, B):
    """ INPUTS: A, B [numpy arrays
        OUTPUTS: a [numpy array]
    
        a is the scaled version of A such that log(a) and B are linearly uncorrelated
        Note: I've numerically tested that the correlation is actually removed.
    """
    num = -np.sum((B - np.mean(B))*(np.log(A) - np.mean(np.log(A))))
    den = np.sum((B - np.mean(B))**2)
    q0 = np.exp(num/den)
    return A*q0**(B - 1), q0


def peakdet(v, delta, x=None):
    """
    Converted from MATLAB script at http://billauer.co.il/peakdet.html

    Returns two arrays

    function [maxtab, mintab]=peakdet(v, delta, x)
    %PEAKDET Detect peaks in a vector
    %        [MAXTAB, MINTAB] = PEAKDET(V, DELTA) finds the local
    %        maxima and minima ("peaks") in the vector V.
    %        MAXTAB and MINTAB consists of two columns. Column 1
    %        contains indices in V, and column 2 the found values.
    %
    %        With [MAXTAB, MINTAB] = PEAKDET(V, DELTA, X) the indices
    %        in MAXTAB and MINTAB are replaced with the corresponding
    %        X-values.
    %
    %        A point is considered a maximum peak if it has the maximal
    %        value, and was preceded (to the left) by a value lower by
    %        DELTA.

    % Eli Billauer, 3.4.05 (Explicitly not copyrighted).
    % This function is released to the public domain; Any use is allowed.

    """
    maxtab = []
    mintab = []

    if x is None:
        x = arange(len(v))

    v = asarray(v)

    if len(v) != len(x):
        sys.exit('Input vectors v and x must have same length')

    if not isscalar(delta):
        sys.exit('Input argument delta must be a scalar')

    if delta <= 0:
        sys.exit('Input argument delta must be positive')

    mn, mx = Inf, -Inf
    mnpos, mxpos = NaN, NaN

    lookformax = True

    for i in arange(len(v)):
        this = v[i]
        if this > mx:
            mx = this
            mxpos = x[i]
        if this < mn:
            mn = this
            mnpos = x[i]

        if lookformax:
            if this < mx-delta:
                maxtab.append((mxpos, mx))
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn+delta:
                mintab.append((mnpos, mn))
                mx = this
                mxpos = x[i]
                lookformax = True

    return array(maxtab), array(mintab)


def getSite():
    tree = etree.parse('/usr/local/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/public/Elder_C_2000-2017.xml')
    root = tree.getroot()

    for element in root.iter():
        if '}' in element.tag:
            bracket_lock = element.tag.index('}')  # The namespace in the tag is enclosed in {}.
            tag = element.tag[bracket_lock + 1:]  # Takes only actual tag, no namespace
            if tag == 'siteName':
                return element.text

def getTimeSeries():
    tree = etree.parse('/usr/local/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/public/Elder_C_2000-2017.xml')
    root = tree.getroot()
    nodata = "-9999"  # default NoData value. The actual NoData value is read from the XML noDataValue tag
    x_value = []
    y_value = []
    site_names = []

    for element in root.iter():
        if '}' in element.tag:
            # print element.tag
            bracket_lock = element.tag.index('}')  # The namespace in the tag is enclosed in {}.
            tag = element.tag[bracket_lock + 1:]  # Takes only actual tag, no namespace
            if tag == 'siteName':
                site_name = element.text

    for element in root.iter():
        if '}' in element.tag:
            # print element.tag
            bracket_lock = element.tag.index('}')  # The namespace in the tag is enclosed in {}.
            tag = element.tag[bracket_lock + 1:]  # Takes only actual tag, no namespace
            if tag == 'value':
                # print element.attrib
                try:
                    n = element.attrib['dateTimeUTC']
                except:
                    n = element.attrib['dateTime']

                v = element.text
                if v == nodata:
                    value = None
                    x_value.append(n)
                    y_value.append(value)
                    site_names.append(site_name)
                else:
                    v = float(element.text)
                    x_value.append(n)
                    y_value.append(v)
                    site_names.append(site_name)

    dates = pd.to_datetime(x_value, format='%Y-%m-%d')
    df = pd.DataFrame({'Site': site_names, 'Time': dates, 'Discharge': y_value})
    # df.to_csv('/usr/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/public/currentdata.csv')
    #
    # dataparse = lambda x: pd.datetime.strptime(x, '%Y-%m-%d')
    # response = urllib.urlopen('http://waterdata.usgs.gov/nwis/dv?cb_00060=on&format=rdb&site_no='
    #                          + gage + '&referred_module=sw&period=&begin_date=' + start + '&end_date=' + stop)
    # tsv = response.read().decode('utf8')
    # tsv = StringIO(tsv)
    #
    # df = pd.read_csv(tsv, sep='\t', header=27, index_col=False, parse_dates=[2], date_parser=dataparse, skiprows=[27])
    # df.columns = ['Agency', 'Site', 'Time', 'Discharge', 'DischargeQualification']
    # df = df[df.DischargeQualification == 'A']
    # df.to_csv('/usr/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/public/needthis.csv')
    return df


def createAbJson(sitesDict, gageNames):
    # for each gage, create abtuples list
    # store in list of abpairs dictionary
    # json'ize that bizness
    abDict = {}
    for gage in gageNames:
        ts = sitesDict[gage]
        a0vals = ts['A0n'][ts['A0n'] > 0].values
        bvals = ts['Bn'][ts['Bn'] > 0].values
        avals = ts['An'][ts['An'] > 0].values
        qvals = ts['qn'][ts['qn'] > 0].values
        bvals = np.ndarray.tolist(bvals)
        a0vals = np.ndarray.tolist(a0vals)
        avals = np.ndarray.tolist(avals)
        qvals = np.ndarray.tolist(qvals)

        abCurrDict = {'b': bvals, 'a0': a0vals, 'a': avals, 'q': qvals}

        # abDict[gage]=[[x,y] for x,y in zip(avals,bvals)];
        abDict[gage] = abCurrDict

    return json.dumps(abDict), abDict

def createStatsInfo(abJson):
    json_readable = json.loads(abJson)
    outliers = []
    categories = []
    series = []
    stats = []
    i = 0
    for gage in json_readable:
        data = json_readable[gage]
        for param in data:
            if param == 'a0' or param == 'b':
                low = np.percentile(data[param], 25)
                med = np.percentile(data[param], 50)
                high = np.percentile(data[param], 75)
                iqr = high - low
                for value in data[param]:
                    if value > ((1.5 * iqr) + high) or value < (low - (1.5 * iqr)):
                        outliers.append(value)
                        data[param].remove(value)
                max = np.max(data[param])
                min = np.min(data[param])
                if param == 'a0':
                    param = 'a'

                categories.append(str(gage) + ', ' + str(param))
                series.append({'name': 'Max', 'type': 'scatter', 'color': colorChooser(i),
                               'marker': {'symbol': 'circle'}, 'data': [[max, i]]})
                series.append({'name': 'Min', 'type': 'scatter', 'color': colorChooser(i),
                               'marker': {'symbol': 'circle'}, 'data': [[min, i]]})
                series.append({'name': 'IQR', 'color': colorChooser(i),
                               'marker': {'symbol': 'circle'}, 'data': [[high, i], [low, i]]})
                series.append({'name': 'Median', 'type': 'scatter', 'color': '#000000',
                               'marker': {'symbol': 'square'}, 'data': [[med, i]]})
                stats.append([str(gage), str(param), "%.2f" % low, "%.2f" % med, "%.2f" % high])
                i += 1
    return {'series': series, 'categories': categories, 'outliers': outliers, 'stats': stats}

def colorChooser(i):
    if i % 2 == 0:
        return '#f7a35c'
    else:
        return '#7cb5ec'
