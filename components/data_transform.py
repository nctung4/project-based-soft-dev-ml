def drop_unnecessary_observations(df_student):
    # Drop old system
    drop_old_system_students = df_student.loc[df_student['AdmissionSemester']
                                              <= '2008-01-01'].index
    df_student.drop(index=drop_old_system_students, inplace=True)

    # Drop finished students
    df_student.drop(
        index=df_student[df_student['StatusId'] == 'Diplomát szerzett'].index, inplace=True)

    # Drop unnecessary cols
    df_student.drop(columns=['ModuleCode', 'LegalRelationshipTerminationReason', 'EnrollmentType', 'Prerequisites',
                    'Recognized', 'EntryType', 'Program', 'DiplomaObtainingDate', 'AdmissionFinancialStatus'], inplace=True)

    # Drop Aláírva
    df_student = df_student[df_student['EntryValue'] != 'Aláírva']

    # Only list valid results
    df_student = df_student[df_student['Valid'] == 'Igaz']

    return df_student


def map_df(df_student):
    # mappings
    grades = {'Jeles': 5,
              'Elégtelen': 1,
              'Megtagadva': -1,
              'Jó': 4,
              'Elégséges': 2,
              'Közepes': 3,
              'teljesítettnek tekintendő': 0,
              'Kiválóan megfelelt (5)': 5,
              'Jól megfelelt': 4}

    df_student['EntryValue'] = df_student['EntryValue'].map(grades)

    map_status = {'Aktív': 0,
                  'Törölt': 1,
                  'Passzív': 0,
                  'Abszolvált': 0,
                  'Sikertelen záróvizsga': 0,
                  'Diplomát szerzett': 0}

    df_student['StatusId'] = df_student['StatusId'].map(map_status)

    map_subject_completed = {'Igaz': 1,
                             'Hamis': 0}

    df_student['Completed'] = df_student['Completed'].map(
        map_subject_completed)

    return df_student


def admission_correction(df_student):
    # Only the first admission is considered
    df_min_admission = df_student.groupby(by='NeptunCode').min()[
        'AdmissionSemester'].reset_index()
    df_student = df_student.join(df_min_admission.rename(columns={
                                 'AdmissionSemester': 'AdmissionSemester_min'}).set_index('NeptunCode'), on='NeptunCode')
    df_student['AdmissionSemester'] = df_student[['AdmissionSemester', 'AdmissionSemester_min']].apply(
        lambda x: x[1] if x[0] != x[1] else x[0], axis=1)

    return df_student


def subject_correction(df_student):
    # Ujrafelvetelizett hallgato --> Ne fogadjuk el a targyakat
    df_student_temp = df_student.loc[df_student['Completed'] == 1]
    df_subject_completed_min_date = df_student_temp.groupby(
        by=['NeptunCode', 'SubjectCode']).min()['Semester'].reset_index()
    df_student = pd.merge(df_student, df_subject_completed_min_date, on=[
                          'NeptunCode', 'SubjectCode'], suffixes=['_original', '_min'], how='left')
    df_student['Semester_min'].fillna(
        df_student['Semester_original'], inplace=True)
    df_student = df_student.loc[df_student['Semester_min']
                                >= df_student['Semester_original']]

    return df_student


def correct_survival_time(df_student):
    groups = df_student.groupby('NeptunCode')
    # Create a dictionary that maps each original rank to its new value for each group
    new_ranks = {}
    for name, group in groups:
        for i, rank in enumerate(sorted(set(group['t']))):
            new_ranks[(name, rank)] = i + 1

    # Update the rank column of the dataframe using the new_ranks dictionary
    df_student['t_new'] = df_student.apply(
        lambda row: new_ranks[(row['NeptunCode'], row['t'])], axis=1)

    return df_student


def add_rownumber(df_student):
    df_student['rn'] = df_student.sort_values(['Semester_original'], ascending=[False]) \
        .groupby(['NeptunCode']) \
        .cumcount() + 1

    return df_student


def calculate_semester_difference(sem1, sem2):
    """Calculate the difference in semesters between two strings"""
    # Extract the academic year and semester from the input strings
    sem1_parts = sem1.split('/')
    sem2_parts = sem2.split('/')
    year1 = sem1_parts[0] + '/' + sem1_parts[1]
    year2 = sem2_parts[0] + '/' + sem2_parts[1]
    sem_num1 = int(sem1_parts[-1])
    sem_num2 = int(sem2_parts[-1])

    # Convert the academic year strings to datetime objects
    year1_start = datetime.strptime(year1+'/1/1', '%Y/%y/%m/%d')
    year2_start = datetime.strptime(year2+'/1/1', '%Y/%y/%m/%d')

    # Calculate the difference in years and semesters between the two academic years
    years = year2_start.year - year1_start.year
    semesters = (year2_start.month - year1_start.month) // 6

    # Calculate the total difference in semesters
    difference = years * 2 + semesters + sem_num2 - sem_num1

    return difference
