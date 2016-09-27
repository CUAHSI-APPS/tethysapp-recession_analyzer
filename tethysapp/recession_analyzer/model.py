# Put your persistent store models in this file
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float
from sqlalchemy.orm import sessionmaker

import pandas as pd
import numpy as np
import urllib2
from io import StringIO

from .app import RecessionAnalyzer

engine = RecessionAnalyzer.get_persistent_store_engine('stream_gage_db')
SessionMaker = sessionmaker(bind=engine)
Base = declarative_base()

class StreamGage(Base):
    __tablename__ = 'stream_gages'
    id  = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    
    def __init__(self,latitude,longitude):
        self.latitude    = latitude
        self.longitude   = longitude
        
        
class TimeSeries():
    def __init__(self,gage,start,stop):
        self.gage = gage
        dateparse = lambda x: pd.datetime.strptime(x, '%Y-%m-%d') # custom function that will be used to make our x axis ticks work right

        response = urllib2.urlopen('http://waterdata.usgs.gov/nwis/dv?cb_00060=on&format=rdb&site_no=' + gage + '&referred_module=sw&period=&begin_date='+start+'&end_date='+stop)
        print response
        tsv = response.read().decode("utf8")
        tsv = StringIO(tsv)
        df = pd.read_csv(tsv,sep='\t',header=26,index_col=False,parse_dates=[2],date_parser=dateparse,skiprows=[27])
        
        df.columns = ['Agency','Site','Time','Discharge','DischargeQualification']
        
        self.time = df.Time
        self.discharge = df.Discharge
        


def getRecessions(gauge,timeSeries,minRecessionLength = 5):
    """
        INPUTS: gauge [string]
                timeSeries [numpy array]
                minRecessionLength [optional integer, default = 10]
                ...some new inputs here
    
        OUTPUT: pandas data frame with columns [Gauge, StarIdx, EndIdx, A, B]
    
        Note: The definition of 'recessing' could use some work -- easily replaced.
        Note: The method for fitting the recession to an (a,b) pair is general and easily replaced.
    """
    q = timeSeries.discharge    

    dq = np.append(0,np.diff(q))    # first derivative (sort of -- dt component...)
    ddq = np.append(np.diff(dq),0)  # second derivative (again, sort of...)
    
    timeSeries.IsReceding = np.logical_and(dq < 0, ddq > 0) # simple definition of recession: dec. and concave down
    
    recessions = []
    start = 0
    A = np.array([])
    B = np.array([])
    for i in range(len(q)):
        if not timeSeries.IsReceding[i]:
            end = i # if we're not receding, set the end to now
            if end - start > minRecessionLength: 
                recessions += [(start,end)]     # if the recession is good, append it (Python note: plus means 'append' here)
                (a,b) = fitRecession(timeSeries.time[start:end],timeSeries.discharge[start:end])
                A = np.append(A,a)
                B = np.append(B,b)    
            start = i+1 # assume that the next time step will start a recession
    
    rec = pd.DataFrame()  
    if len(recessions) == 0: return rec  
    
    rec['StartIdx']   = [start for (start,end) in recessions]
    rec['EndIdx']     = [end for (start,end) in recessions]

    # decorrelate the (a,b) point cloud -- this only affects the a values
    A = BergnerZouhar(A,B)    
    rec['A'] = A
    rec['B'] = B
    
    return rec

def fitRecession(time,discharge):
    """ INPUTS: time [numpy array]
                discharge [numpy array]
    
        OUTPUTS: recession parameter (a,b) pair
    
        This is a very simple fitting procedure, but it can easily be superceded.
    """
    dq = np.diff(discharge)
    p = np.polyfit(np.log(discharge[1:]),np.log(-dq),1)
    return (np.exp(p[1]),p[0]) #(a,b)
    
def BergnerZouhar(A,B):
    """ INPUTS: A, B [numpy arrays
        OUTPUTS: a [numpy array]
    
        a is the scaled version of A such that log(a) and B are linearly uncorrelated
        Note: I've numerically tested that the correlation is actually removed.
    """
    num = -np.sum((B - np.mean(B))*(np.log(A) - np.mean(np.log(A))))
    den = np.sum((B - np.mean(B))**2)
    q0 = np.exp(num/den)
    return A*q0**(B-1)    