import pandas
from ortools.sat.python import cp_model
num_doctors = 4
num_shifts = 4
num_days = 7
all_doctors = range(num_doctors)
all_shifts = range(num_shifts)
all_days = range(num_days)



# read data from excel files
doctordf = pandas.read_excel("doctors.xlsx", header=0) 
doctors_data = {}
for iteration in doctordf.iterrows(): 
    row = iteration[1] 
    name = row[0] 
    doctors_data[name] = {} 
    doctors_data[name]["state_coverage"] = row[1] 
    doctors_data[name]["priority"] = row[2] 
    doctors_data[name]["can_hypertension"] = row[3] 
    doctors_data[name]["can_diabetes"] = row[4] 
    doctors_data[name]["shift_available"] = [] 
    for day in range(num_days): 
        dayList = []
        for shift in range(num_shifts): 
            dayList.append(
                int((shift*6 >= row[5 + day * 2]) and ((shift+1)*6 <= row[5 + day*2 + 1]))
            )
        doctors_data[name]["shift_available"].append(dayList)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

patients =list(chunks(pandas.read_excel("./patients.xlsx", header=0).loc[0].tolist(), num_shifts))

max_patients_shift = []

for i in range(num_days):
    maxItem = patients[i][0]
    maxItemIndex = 0
    for j in range(num_shifts):
        if patients[i][j] > maxItem:
            maxItem = patients[i][j]
            maxItemIndex = j
    max_patients_shift.append(maxItemIndex)


# add variables
model = cp_model.CpModel()
for doctor in doctors_data.keys():
        doctors_data[doctor]["worked_shifts"] = []
        doctors_data[doctor]["hyper_shifts"] = []
        doctors_data[doctor]["diabetes_shifts"] = []
        for day,index in zip(doctors_data[doctor]["shift_available"], all_days):
            doctors_data[doctor]["worked_shifts"].append([])
            doctors_data[doctor]["hyper_shifts"].append([])
            doctors_data[doctor]["diabetes_shifts"].append([])
            for (shift,sindex) in zip(day,all_shifts):
                doctors_data[doctor]["worked_shifts"][index].append(model.NewBoolVar('w_shift_doc%sd%is%i' % (doctor, index, sindex)))
                doctors_data[doctor]["hyper_shifts"][index].append(model.NewBoolVar('h_shift_doc%sd%is%i' % (doctor, index, sindex)))
                doctors_data[doctor]["diabetes_shifts"][index].append(model.NewBoolVar('d_shift_doc%sd%is%i' % (doctor, index, sindex)))


for (s,d) in zip(max_patients_shift, range(len(max_patients_shift))):
     model.Add(sum(doctors_data[doctor]["worked_shifts"][d][s] for doctor in doctors_data.keys()) == 2)

for dindex in all_days:
    for sindex in all_shifts:
        if(max_patients_shift[dindex] != sindex):
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["worked_shifts"][dindex][sindex] for doctor in doctors_data.keys()) <= 1)
                   
for dindex in all_days:
    for sindex in all_shifts:
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["hyper_shifts"][dindex][sindex] for doctor in doctors_data.keys()) <= 1)

for dindex in all_days:
    for sindex in all_shifts:
            print(dindex,sindex)
            model.Add(sum(doctors_data[doctor]["diabetes_shifts"][dindex][sindex] for doctor in doctors_data.keys()) <= 1)

hypertension_days = list((model.NewBoolVar("hyper_day%s" % day) for day in all_days))
diabetes_days = list((model.NewBoolVar("diabetes_day%s" % day) for day in all_days))


for dindex in all_days:
    hy_day= hypertension_days[dindex]
    sum_value = sum(
    doctors_data[doctor]["hyper_shifts"][dindex][sindex] 
    for doctor in doctors_data.keys()
    for sindex in all_shifts
    )
    model.Add(sum_value == num_shifts).OnlyEnforceIf(hy_day)
    model.Add(sum_value == 0).OnlyEnforceIf(hy_day.Not())

for dindex in all_days:
    hy_day= diabetes_days[dindex]
    sum_value = sum(
    doctors_data[doctor]["diabetes_shifts"][dindex][sindex] 
    for doctor in doctors_data.keys()
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
        for doctor in doctors_data.keys() 
        for (day,dindex) in zip(doctors_data[doctor]["worked_shifts"], all_days)
        for (shift,sindex) in zip(day,all_shifts))
        +
        sum(
            doctors_data[doctor]["can_hypertension"] *
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"] + doctors_data[doctor]["state_coverage"])
        for doctor in doctors_data.keys() 
        for (day,dindex) in zip(doctors_data[doctor]["hyper_shifts"], all_days)
        for (shift,sindex) in zip(day,all_shifts))
        +
        sum(
            doctors_data[doctor]["can_diabetes"] *
            doctors_data[doctor]["shift_available"][dindex][sindex] * shift *
            (100 * doctors_data[doctor]["priority"] + doctors_data[doctor]["state_coverage"])
        for doctor in doctors_data.keys() 
        for (day,dindex) in zip(doctors_data[doctor]["diabetes_shifts"], all_days)
        for (shift,sindex) in zip(day,all_shifts))
        )


solver = cp_model.CpSolver()
#solver.parameters.linearization_level = 0
#doctors_data["doctor1"]["worked_shifts"][0][0]
status = solver.Solve(model)
#if(status == cp_model.OPTIMAL):
#    print("solution:")
#    for doctor in doctors_data.keys():
#        print(doctor)
#        for (day,dindex) in zip(doctors_data[doctor]["worked_shifts"], all_days):
#            print("Day",dindex)
#            for (shift,sindex) in zip(day,all_shifts):
#                print("shift",sindex, solver.Value(doctors_data[doctor]["worked_shifts"][dindex][sindex]))

#print(list(solver.Value(s) for d in doctors_data["doctor17"]["worked_shifts"] for s in d))
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



        
print("solution hypertension clinic:")
for doctor in doctors_data.keys():
    print(doctor)
    for (day,dindex) in zip(doctors_data[doctor]["hyper_shifts"], all_days):
        if(any(map(lambda x : solver.Value(x),day))):
            for (shift,sindex) in zip(day,all_shifts):
                assigned = solver.Value(shift)
                if(assigned == 1):
                    print("Day",dindex, end=' ')
                    print("shift",sindex, solver.Value(shift))
            print()

print("solution diabetes clinic:")
for doctor in doctors_data.keys():
    print(doctor)
    for (day,dindex) in zip(doctors_data[doctor]["diabetes_shifts"], all_days):
        if(any(map(lambda x : solver.Value(x),day))):
            for (shift,sindex) in zip(day,all_shifts):
                assigned = solver.Value(shift)
                if(assigned == 1):
                    print("Day",dindex, end=' ')
                    print("shift",sindex, solver.Value(shift))
            print()
