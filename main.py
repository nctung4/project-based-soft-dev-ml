import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
from datetime import datetime
from sklearn.impute import KNNImputer
from sksurv.ensemble import RandomSurvivalForest
from helper.logger import logging
from components.data_transform import *
from components.data_ingest import load_data_from_sql

# Config
logger = logging.getLogger(__name__)

# model and imputer
filename = './artifacts/knn_imputer.pkl'
imputer = pickle.load(open(filename, 'rb'))
filename_2 = './artifacts/random_survival_forest.pkl'
rsf = pickle.load(open(filename_2, 'rb'))


def main():
    logger.info('Python script execution has started.')
    logger.info('Data preparation started.')
    df_student = pd.read_excel('./dataset/NeptunExport_merged.xlsx')
    df_student = drop_unnecessary_observations(df_student)
    df_student = map_df(df_student)
    # Language exam var.
    df_student['language_exam_available'] = df_student['LanguageExamFulfillmentDate'].apply(
        lambda x: 0 if pd.isnull(x) else 1)
    df_student = admission_correction(df_student)
    df_student = subject_correction(df_student)
    df_student['t'] = df_student[['AdmissionSemester', 'Semester_original']].apply(
        lambda x: calculate_semester_difference(x[0], x[1]), axis=1)
    df_student['t'] = df_student['t']+1
    df_student = correct_survival_time(df_student)
    df_student = add_rownumber(df_student)

    df_avg_credit_in_semester_temp = df_student[['NeptunCode', 't_new', 'EnrollmentCredit']].groupby(
        by=['NeptunCode', 't_new']).sum().reset_index()
    df_avg_credit_in_semester = df_avg_credit_in_semester_temp.groupby(
        by='NeptunCode').mean()['EnrollmentCredit'].reset_index()

    df_subjects_mean = df_student[['NeptunCode', 'Completed', 'SubjectTakenCount']].groupby(
        by='NeptunCode').mean().reset_index()

    df_weighted_avg_temp = df_student[df_student['EntryValue'] != -1]

    def calculate_weighted(x):
        try:
            return np.average(x, weights=df_weighted_avg_temp.loc[x.index, 'EnrollmentCredit'])
        except:
            return np.nan

    weighted_avg = df_weighted_avg_temp.groupby(
        'NeptunCode')['EntryValue'].apply(calculate_weighted)
    weighted_avg = weighted_avg.reset_index()

    df_score = df_student.loc[df_student['rn'] == 1, [
        'NeptunCode', 't_new', 'StatusId', 'AdmissionScoreTotal', 'language_exam_available']]
    df_score = df_score.join(df_avg_credit_in_semester.set_index(
        'NeptunCode'), on='NeptunCode', how='left')
    df_score = df_score.join(df_subjects_mean.set_index(
        'NeptunCode'), on='NeptunCode', how='left')
    df_score = df_score.join(weighted_avg.set_index(
        'NeptunCode'), on='NeptunCode', how='left')
    df_score['StatusId'] = df_score['StatusId'].astype(bool)
    df_score.rename(columns={'t_new': 't'}, inplace=True)
    df_score[['AdmissionScoreTotal', 'EnrollmentCredit', 'Completed', 'SubjectTakenCount', 'EntryValue']] = imputer.transform(
        df_score[['AdmissionScoreTotal', 'EnrollmentCredit', 'Completed', 'SubjectTakenCount', 'EntryValue']])
    df_score = df_score[~df_score['StatusId']]
    df_final = df_score[['NeptunCode']]
    df_score = df_score.iloc[:, 3:]
    logger.info('Data preparation finished.')
    logger.info('Data scoring started.')
    surv_func_pred = rsf.predict_survival_function(df_score, return_array=True)
    surv_func_df = pd.DataFrame(surv_func_pred, columns=['semester_1', 'semester_2', 'semester_3', 'semester_4', 'semester_5',
                                'semester_6', 'semester_7', 'semester_8', 'semester_9', 'semester_10', 'semester_11'], index=df_score.index)
    risk_score_pred = rsf.predict(df_score)

    df_final = pd.concat([df_final, surv_func_df], axis=1)
    df_final['risk_score'] = risk_score_pred
    logger.info('Data scoring finished.')
    logger.info('Python script execution has finished.')
    df_final.to_pickle('./artifacts/test.pkl')


if __name__ == '__main__':
    main()
