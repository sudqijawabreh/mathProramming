import pandas as pd
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import numpy as np

def getDateIndex(date):
    for i in range(len(dates)):
        if dates[i] == pd.to_datetime(date):
            return i


doctordf = pd.read_excel("./monday_Doctors_availble_time.xlsx", header=0) 
#doctordf = pd.read_excel("./doctors - Copy.xlsx",sheet_name="Sheet2", header=0) 


two_doctors_shift_patient_number = 10
doctordf=doctordf.iloc[:,: 10]

max1=pd.to_datetime(max(doctordf['Date'])).day
min1=pd.to_datetime(min(doctordf['Date'])).day
diff=max1-min1+1
dates=pd.to_datetime(doctordf['Date']).dt.date
dates=pd.DatetimeIndex(sorted(dates.unique()))

for i in dates:
    print(i.date())
    print(i.weekday())

# num of days in all the month
num_days = len(dates)
all_days = range(num_days)
all_days_in_weeks = range((num_days // 7) * 7)

patientsdf =pd.read_csv("./patient_byweekday_14hour.csv", header=0)
num_shifts = len(patientsdf['hourly_period_rank'].unique())
all_shifts = range(num_shifts)
shift_period = 24 // num_shifts
# num of patients for everyday in the month
patients = [ [0 for i in range(num_shifts)] for j in range(num_days)]
# num of patients weekly 
weekly_patients_schedual = [ [0 for i in range(num_shifts)] for j in range(7)]
for iteration in patientsdf.iterrows(): 
    row = iteration[1] 
    shiftNumber = int(row[1])
    week_day = int(row[0]) - 1
    day_patients_num = row[2]
    weekly_patients_schedual[week_day][shiftNumber] = day_patients_num

for (date,day) in zip(dates,range(num_days)):
    for shift in range(num_shifts):
        date_week_day = date.weekday()
        patients[day][shift] = weekly_patients_schedual[date_week_day][shift]

two_doctors_shifts = []

for i in range(num_days):
    for j in range(num_shifts):
        if patients[i][j] > two_doctors_shift_patient_number:
            two_doctors_shifts.append((i,j))



doctors_data = {}

for iteration in doctordf.iterrows(): 
    row = iteration[1] 
    name = row[0] 
    doctors_data[name] = {} 
    doctors_data[name]["fixed"] = row[4]
    doctors_data[name]["priority"] = row[5] 
    doctors_data[name]["can_hypertension"] = row[6] 
    # TODO Add coloumn for diabetes
    doctors_data[name]["can_diabetes"] = row[6] 
    doctors_data[name]["shift_available"] = [[0 for i in range(num_shifts)] for j in range(num_days)]
    doctors_data[name]["requested_hours"] = [0 for j in range(num_days)]
    

for iteration in doctordf.iterrows(): 
    row = iteration[1] 
    name = row[0] 
    row_date = row[1]
    for shift in range(num_shifts): 
        start_hour = int(row[2][0:2])
        end_hour = int(row[3][0:2])
        value =  int((shift * shift_period >= start_hour) and ((shift+1) * shift_period <= end_hour))
        existing = doctors_data[name]["shift_available"][getDateIndex(row_date)][shift]
        doctors_data[name]["shift_available"][getDateIndex(row_date)][shift] = existing or value
        doctors_data[name]["requested_hours"][getDateIndex(row_date)] = int(row[7])
        print(getDateIndex(row_date))
        print(name,row_date,shift,value,start_hour,end_hour)
    if doctors_data[name]["fixed"] == 1:
        one_day = doctors_data[name]["shift_available"][getDateIndex(row_date)]
        for day in all_days:
            doctors_data[name]["shift_available"][day] = one_day



all_non_fixed_doctors = [doctor for doctor in doctors_data.keys() if doctors_data[doctor]['fixed'] == 0]
all_fixed_doctors = [doctor for doctor in doctors_data.keys() if doctors_data[doctor]['fixed'] == 1]
all_doctors = [doctor for doctor in doctors_data.keys()]


for (i,s) in two_doctors_shifts:
    print(i,s)
    patients[i][s]

# add variables
model = cp_model.CpModel()
for doctor in all_doctors:
        doctors_data[doctor]["worked_shifts"] = []
        doctors_data[doctor]["hyper_shifts"] = []
        doctors_data[doctor]["diabetes_shifts"] = []
        for day,index in zip(doctors_data[doctor]["shift_available"], all_days):
            doctors_data[doctor]["worked_shifts"].append([])
            doctors_data[doctor]["hyper_shifts"].append([])
            doctors_data[doctor]["diabetes_shifts"].append([])
            for (shift,sindex) in zip(day,all_shifts):
                doctors_data[doctor]["worked_shifts"][index].append(model.NewBoolVar('w_shift_doc%sd%is%i' % (doctor, index, sindex)))
                if (doctors_data[doctor]["fixed"] == 0):
                    doctors_data[doctor]["hyper_shifts"][index].append(model.NewBoolVar('h_shift_doc%sd%is%i' % (doctor, index, sindex)))
                    doctors_data[doctor]["diabetes_shifts"][index].append(model.NewBoolVar('d_shift_doc%sd%is%i' % (doctor, index, sindex)))


for doctor in all_fixed_doctors:
    for day,index in zip(doctors_data[doctor]["shift_available"], all_days):
            for (shift,sindex) in zip(day,all_shifts):
                if doctors_data[doctor]["shift_available"][index][sindex] == 1:
                    print(doctors_data[doctor]["worked_shifts"][index][sindex] == 1)
                    model.Add(doctors_data[doctor]["worked_shifts"][index][sindex] == 1)
                else:
                    model.Add(doctors_data[doctor]["worked_shifts"][index][sindex] == 0)

for doctor in all_doctors:
    for day,index in zip(doctors_data[doctor]["shift_available"], all_days):
            for (shift,sindex) in zip(day,all_shifts):
                if doctors_data[doctor]["shift_available"][index][sindex] == 0:
                    model.Add(doctors_data[doctor]["worked_shifts"][index][sindex] == 0)

for doctor in all_doctors:
    print(doctor)

for doctor in all_non_fixed_doctors:
    for index in (all_days):
            model.Add( sum(doctors_data[doctor]["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data[doctor]["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Abigail Bienenfeld']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Abigail Bienenfeld']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Batya Zuckerman']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Batya Zuckerman']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Dan Frimerman']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Dan Frimerman']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Deena Wasserman']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Deena Wasserman']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Eliana Megerman']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Eliana Megerman']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Evgeni Kontrient']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Evgeni Kontrient']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Geoffrey Kamen']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Geoffrey Kamen']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Georgina Haden']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Georgina Haden']["requested_hours"][index])
        #model.Add( sum(doctors_data['Dr. Lindsay Agolia']["worked_shifts"][index][sindex] for sindex in all_shifts) <= doctors_data['Dr. Lindsay Agolia']["requested_hours"][index])









#

for (d,s) in two_doctors_shifts:
     model.Add(sum(doctors_data[doctor]["worked_shifts"][d][s] for doctor in all_doctors) <= 2)


for dindex in all_days:
    for sindex in all_shifts:
        if not (dindex, sindex) in two_doctors_shifts:
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["worked_shifts"][dindex][sindex] for doctor in all_doctors ) <= 1)

                   
for dindex in all_days_in_weeks:
    for sindex in all_shifts:
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["hyper_shifts"][dindex][sindex] for doctor in all_non_fixed_doctors) <= 1)

for dindex in all_days_in_weeks:
    for sindex in all_shifts:
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["diabetes_shifts"][dindex][sindex] for doctor in all_non_fixed_doctors) <= 1)

hypertension_days = list((model.NewBoolVar("hyper_day%s" % day) for day in all_days_in_weeks))
diabetes_days = list((model.NewBoolVar("diabetes_day%s" % day) for day in all_days_in_weeks))


for dindex in all_days_in_weeks:
    hy_day= hypertension_days[dindex]
    sum_value = sum(
    doctors_data[doctor]["hyper_shifts"][dindex][sindex] 
    for doctor in all_non_fixed_doctors
    for sindex in all_shifts
    )
    model.Add(sum_value <= num_shifts).OnlyEnforceIf(hy_day)
    model.Add(sum_value > 0).OnlyEnforceIf(hy_day)
    model.Add(sum_value == 0).OnlyEnforceIf(hy_day.Not())

for dindex in all_days_in_weeks:
    hy_day= diabetes_days[dindex]
    sum_value = sum(
    doctors_data[doctor]["diabetes_shifts"][dindex][sindex] 
    for doctor in all_non_fixed_doctors
    for sindex in all_shifts
    )
    model.Add(sum_value <= num_shifts).OnlyEnforceIf(hy_day)
    model.Add(sum_value > 0).OnlyEnforceIf(hy_day)
    model.Add(sum_value == 0).OnlyEnforceIf(hy_day.Not())
   

for week in (all_days_in_weeks // 7):
    hyper_shifts_sum = sum(hypertension_days[week * 7 : (week + 1) * 7])
    model.Add(hyper_shifts_sum >= 3)
    model.Add(hyper_shifts_sum <= 4)
    diabetes_shifts_sum = sum(diabetes_days[week * 7 : (week + 1) * 7])
    model.Add(diabetes_shifts_sum >= 3)
    model.Add(diabetes_shifts_sum <= 4)


# shift = if doctor takes shift or not 0,1
# shift_available if doctor is available in that shift
# priority * 100 to firt priorites doctor priority then maximize for state_coverage
# since state_coverage max value is 50
model.Maximize(
        sum(
             shift *
            (100 * doctors_data[doctor]["priority"])
        for doctor in all_doctors
        for (day,dindex) in zip(doctors_data[doctor]["worked_shifts"], all_days)
        for (shift,sindex) in zip(day,all_shifts))
        +
        sum(
            doctors_data[doctor]["can_hypertension"] *
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"])
        for doctor in all_non_fixed_doctors
        for (day,dindex) in zip(doctors_data[doctor]["hyper_shifts"], all_days_in_weeks)
        for (shift,sindex) in zip(day,all_shifts))
        +
        sum(
            doctors_data[doctor]["can_diabetes"] *
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"])
        for doctor in all_non_fixed_doctors 
        for (day,dindex) in zip(doctors_data[doctor]["diabetes_shifts"], all_days_in_weeks)
        for (shift,sindex) in zip(day,all_shifts))
        )

solver = cp_model.CpSolver()
status = solver.Solve(model)


if(status == cp_model.INFEASIBLE):
    print("solution is infeaisble with the current input and constrains")

if(status == cp_model.OPTIMAL):
    print("solution primary:")
    for doctor in doctors_data.keys():
        print(doctor)
        for (day,dindex) in zip(doctors_data[doctor]["worked_shifts"], all_days):
            if(any(map(lambda x : solver.Value(x),day))):
                for (shift,sindex) in zip(day,all_shifts):
                    assigned = solver.Value(shift)
                    if(assigned == 1):
                        print("Day",dates[dindex],dindex, end=' ')
                        print("shift",sindex, solver.Value(shift))
                print()




if(status == cp_model.OPTIMAL):
    print("solution hypertension clinic:")
    for doctor in doctors_data.keys():
        print(doctor)
        for (day,dindex) in zip(doctors_data[doctor]["hyper_shifts"], all_days_in_weeks):
            if(any(map(lambda x : solver.Value(x),day))):
                for (shift,sindex) in zip(day,all_shifts):
                    assigned = solver.Value(shift)
                    if(assigned == 1):
                        print("Day",dindex, end=' ')
                        print("shift",sindex, solver.Value(shift))
                print()

if(status == cp_model.OPTIMAL):
    print("solution diabetes clinic:")
    for doctor in doctors_data.keys():
        print(doctor)
        for (day,dindex) in zip(doctors_data[doctor]["diabetes_shifts"], all_days_in_weeks):
            if(any(map(lambda x : solver.Value(x),day))):
                for (shift,sindex) in zip(day,all_shifts):
                    assigned = solver.Value(shift)
                    if(assigned == 1):
                        print("Day",dates[dindex].date(),dindex, end=' ')
                        print("shift",sindex, solver.Value(shift))
                print()





