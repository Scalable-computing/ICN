# -*- coding: utf-8 -*-
"""
Created on Tue Nov 22 14:40:44 2022

@author: Jeroen Lemsom
"""
import numpy as np
import time
import datetime
import math


class Sensor:
 
    #Sensor Constructor which takes the name and the location of the temperature sensor as inputs
    def __init__(self, name, interval):
        self.name = name
        self.interval = interval
        self.last_update = 0
        path = './temps/temperatures_' + self.name + '.csv'
        print(path)
        df = np.genfromtxt(path, delimiter=',')
        df = df[1:,:]
        start = datetime.datetime(2012, 1, 1) #Retrieve historical weather data over the last 10 years
        end = datetime.datetime(2021, 12, 31)
        difference = end - start
        numdays = difference.days
        dates = [start + datetime.timedelta(days=x) for x in range(numdays)]
        
        self.time = np.array(dates)
        self.tavg = df[1:,1]
        self.tmin = df[1:,2]
        self.tmax = df[1:,3]

        self.lastvalue = self.get_longtermaverage()
    
    def getValue(self):
        return (self.lastvalue, self.interval)

    def update(self):
        t = time.time()
        if t >= (self.last_update + self.interval):
            self.last_update = t
            self.get_update()

    #This method returns a kernel weighted longterm average temperature for a specific day in the year
    def get_longtermaverage(self):
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day
        #Filter historical data on data which has the same date (eg 23st of November) in different years
        tavg_sub = []

        for i in range(len(self.time)):
            if(self.time[i].day == day and self.time[i].month == month):
                tavg_sub.append(self.tavg[i])

        t = np.arange(1,len(tavg_sub)+1) 
        utilities = 1.5 * (1 - np.power(t,2))
        weights = utilities/sum(utilities)

        weighted_values = weights * tavg_sub
        weighted_tavg = sum(weighted_values)
        return weighted_tavg
    
    
    #On top of the get_longtermaverage method, this method adjusts the average temperature for specific hours during the day using linear interpolation
    def get_longtermaverage_corrected_for_dayhour(self):
        
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day
        #Filter historical data on data which has the same date (eg 23st of November) in different years
        tmin_sub = []
        tmax_sub = []
        
        for i in range(len(self.time)):
            if(self.time[i].day == day and self.time[i].month == month):
                tmin_sub.append(self.tmin[i])
                tmax_sub.append(self.tmax[i])

        t = np.arange(1,len(tmin_sub)+1) 
        utilities = 1.5 * (1 - np.power(t,2))
        weights = utilities/sum(utilities)

        weighted_tmin = sum(weights * tmin_sub)
        weighted_tmax = sum(weights * tmax_sub)
        
        hour = datetime.datetime.now().hour
        corrected_hour = abs(hour - 12) #difference in hours from 12
        longterm_avg_temp = self.get_longtermaverage()
        half_interval = weighted_tmax - weighted_tmin
        increment = half_interval/12
        longtermaverage_corrected_for_dayhour = weighted_tmax - increment*corrected_hour
        return longtermaverage_corrected_for_dayhour
    
    #This method calculates the historical standard deviation of 
    def get_longtermstandarddev(self):
        #Filter historical data on data which has the same date (eg 23st of November) in different years
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day
        
        tmin_sub = []
        tmax_sub = []

        for i in range(len(self.time)):
            if(self.time[i].day == day and self.time[i].month == month):
                tmin_sub.append(self.tmin[i])
                tmax_sub.append(self.tmax[i])
                
        t = np.arange(1,len(tmin_sub)+1) 
        utilities = 1.5 * (1 - np.power(t,2))
        weights = utilities/sum(utilities)

        weighted_tmin = sum(weights * tmin_sub)
        weighted_tmax = sum(weights * tmax_sub)        

        daily_stddev = (weighted_tmax - weighted_tmin)/4 #appromate std deviation using range
        
        return daily_stddev
    
    #Update of the Prediction
    #The Prediction is based on (1) the kernel weighted historical average on the day corrected for the specific hourj and (2) the previous prediction
    def get_update(self):
        longtermaverage_corrected_for_dayhour = self.get_longtermaverage_corrected_for_dayhour()
        #Assign weights of 0.2 and 0.8 to the long term and short term component respectively
        mean = ((0.2*longtermaverage_corrected_for_dayhour) + 0.8*self.lastvalue)
        std_dev = self.get_longtermstandarddev()/math.sqrt(24*60) #decrease daily std dev to a smaller value to represent noise in minute data
        prediction = np.random.normal(mean, std_dev) #simulate using a normal distr approximation of temperatures
        self.lastvalue = prediction
        return prediction