import pandas as pd
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import numpy as np

def getDateIndex(date):
    for i in range(len(dates)):
        if dates[i] == pd.to_datetime(date):
            return i


doctordf = pd.read_excel("./final_doctor.xlsx", header=0) 
#doctordf = pd.read_excel("./doctors - Copy.xlsx",sheet_name="Sheet2", header=0) 


doctordf=doctordf.iloc[:,: 10]

max1=pd.to_datetime(max(doctordf['date'])).day
min1=pd.to_datetime(min(doctordf['date'])).day
diff=max1-min1+1
dates=pd.to_datetime(doctordf['date']).dt.date
dates=pd.DatetimeIndex(sorted(dates.unique()))

for i in dates:
    print(i.date())

num_days = diff
all_days = range(num_days)
all_days_in_weeks = range((num_days // 7) * 7)

patientsdf =pd.read_csv("./shfits.csv", header=0)
num_shifts = len(patientsdf['hourly_period_rank'].unique())
all_shifts = range(num_shifts)
shift_period = 24 // num_shifts
patients = [ [0 for i in range(num_shifts)] for j in range(num_days)]
for iteration in patientsdf.iterrows(): 
    row = iteration[1] 
    shiftNumber = int(row[2]) - 1
    row_date = row[0]
    day_patients_num = row[3]
    print(row_date,getDateIndex(row_date),day_patients_num)
    index = getDateIndex(row_date)
    if index is None:
        print("date %s doesn't match any dates from doctors shifts" % row_date)
        continue
    patients[getDateIndex(row_date)][shiftNumber] = day_patients_num

max_patients_shift = []

for i in range(num_days):
    maxItem = patients[i][0]
    maxItemIndex = 0
    for j in range(num_shifts):
        if patients[i][j] > maxItem:
            maxItem = patients[i][j]
            maxItemIndex = j
    max_patients_shift.append(maxItemIndex)



doctors_data = {}

for iteration in doctordf.iterrows(): 
    row = iteration[1] 
    name = row[0] 
    print(name,row[9])
    doctors_data[name] = {} 
    doctors_data[name]["state_coverage"] = row[1] 
    doctors_data[name]["priority"] = row[2] 
    doctors_data[name]["can_hypertension"] = row[3] 
    doctors_data[name]["can_diabetes"] = row[4] 
    doctors_data[name]["shift_available"] = [[0 for i in range(num_shifts)] for j in range(num_days)]
    doctors_data[name]["fixed"] = row[9]
    

for iteration in doctordf.iterrows(): 
    row = iteration[1] 
    name = row[0] 
    row_date = row[5]
    for shift in range(num_shifts): 
        value =  int((shift * shift_period >= row[7]) and ((shift+1) * shift_period <= row[8]))
        existing = doctors_data[name]["shift_available"][getDateIndex(row_date)][shift]
        doctors_data[name]["shift_available"][getDateIndex(row_date)][shift] = existing or value
        print(getDateIndex(row_date))
        print(name,row_date,shift,value,row[7],row[8])
    if doctors_data[name]["fixed"] == 1:
        one_day = doctors_data[name]["shift_available"][getDateIndex(row_date)]
        for day in all_days:
            doctors_data[name]["shift_available"][day] = one_day



all_non_fixed_doctors = [doctor for doctor in doctors_data.keys() if doctors_data[doctor]['fixed'] == 0]
all_fixed_doctors = [doctor for doctor in doctors_data.keys() if doctors_data[doctor]['fixed'] == 1]
all_doctors = [doctor for doctor in doctors_data.keys()]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


for (i,s) in zip(range(num_days),max_patients_shift):
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



for (s,d) in zip(max_patients_shift, range(len(max_patients_shift))):
     model.Add(sum(doctors_data[doctor]["worked_shifts"][d][s] for doctor in all_doctors) == 2)

for dindex in all_days:
    for sindex in all_shifts:
        if(max_patients_shift[dindex] != sindex):
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["worked_shifts"][dindex][sindex] for doctor in all_doctors ) == 1)

                   
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
    model.Add(sum_value == num_shifts).OnlyEnforceIf(hy_day)
    model.Add(sum_value == 0).OnlyEnforceIf(hy_day.Not())

for dindex in all_days_in_weeks:
    hy_day= diabetes_days[dindex]
    sum_value = sum(
    doctors_data[doctor]["diabetes_shifts"][dindex][sindex] 
    for doctor in all_non_fixed_doctors
    for sindex in all_shifts
    )
    model.Add(sum_value == num_shifts).OnlyEnforceIf(hy_day)
    model.Add(sum_value == 0).OnlyEnforceIf(hy_day.Not())
   

hyper_shifts_sum = sum(hypertension_days)
model.Add(hyper_shifts_sum >= 3)
model.Add(hyper_shifts_sum <= 4)

diabetes_shifts_sum = sum(diabetes_days)
model.Add(diabetes_shifts_sum >= 3)
model.Add(diabetes_shifts_sum <= 4)




# shift = if doctor takes shift or not 0,1
# shift_available if doctor is available in that shift
# priority * 100 to firt priorites doctor priority then maximize for state_coverage
# since state_coverage max value is 50
model.Maximize(
        sum(
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"] + doctors_data[doctor]["state_coverage"])
        for doctor in all_doctors
        for (day,dindex) in zip(doctors_data[doctor]["worked_shifts"], all_days)
        for (shift,sindex) in zip(day,all_shifts))
        +
        sum(
            doctors_data[doctor]["can_hypertension"] *
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"] + doctors_data[doctor]["state_coverage"])
        for doctor in all_non_fixed_doctors
        for (day,dindex) in zip(doctors_data[doctor]["hyper_shifts"], all_days_in_weeks)
        for (shift,sindex) in zip(day,all_shifts))
        +
        sum(
            doctors_data[doctor]["can_diabetes"] *
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"] + doctors_data[doctor]["state_coverage"])
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
                        print("Day",dindex, end=' ')
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
                        print("Day",dindex, end=' ')
                        print("shift",sindex, solver.Value(shift))
                print()





