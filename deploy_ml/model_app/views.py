from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
import os
import time
from collections.abc import Mapping
import gc
import math
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
from fuzzywuzzy import fuzz

s1 = u'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'
s0 = u'AAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
def remove_VN_accents(input_str):
    s = ''
    print(input_str.encode('utf-8'))
    for c in input_str:
        if c in s1:
            s += s0[s1.index(c)]
        else:
            s += c
    return s

def Model(Major,Semester):
    if int(Semester) <= 0 or int(Semester) >= 8:
        return
    Major = remove_VN_accents(Major)
    Major = Major.replace(" ", "")
    Major = Major.lower()    
    Majors = ["hethongthongtin","congnghethongtin","kythuatphanmem","khoahocmaytinh","khoahocdulieu"]
    if Major not in Majors:
        return 
    df_course = pd.read_csv(("..\data\major_"+Major+"_course.csv"),
        usecols=['CourseID', 'Name', 'Url', 'Code'],
        dtype={'CourseID': 'int32', 'Name': 'str', 'Url': 'str', 'Code': 'str'})
    df_study = pd.read_csv(("..\data\major_"+Major+"_studyornot.csv"),
        usecols=['StudentID', 'CourseID','Name','StudyOrNot','Semester','Group'],
        dtype={'StudentID': 'int32', 'CourseID': 'int32', 'Name': 'str', 'StudyOrNot': 'int32', 'Semester': 'int32','Group': 'int32'})
    df_study = df_study.loc[(df_study.Name == 'Những môn chính học kỳ'+' '+Semester) | ((df_study.Semester == int(Semester) + 1 ) & (df_study.Group != 0))]
    df_study_tmp = pd.DataFrame(df_study.groupby('StudyOrNot').size(), columns=['Count'])
    ############ Tự chọn nhóm 1 
    if 1 in df_study.Group.values:
        print("\n")
        df_study1 = df_study.loc[(df_study.Name == 'Những môn chính học kỳ' +' '+Semester) | ((df_study.Semester == int(Semester) + 1) & (df_study.Group != 0) & (df_study.Group == 1))]
        df_study_tmp = pd.DataFrame(df_study1.groupby('StudyOrNot').size(), columns=['Count'])
        df_course_cnt = pd.DataFrame(df_study1.groupby('CourseID').size(), columns=['count'])
        #filter data
        popularity_thres = 3
        popular_course = list(set(df_course_cnt.query('count >= @popularity_thres').index))
        df_study_drop_course = df_study1[df_study1.CourseID.isin(popular_course)]
        df_study_cnt = pd.DataFrame(df_study_drop_course.groupby('CourseID').size(), columns=['count'])
        df_study_cnt.head()
        # filter data
        study_thres = 3
        active_student = list(set(df_study_cnt.query('count >= @study_thres').index))
        df_study_drop_student = df_study_drop_course[df_study_drop_course.StudentID.isin(active_student)]
        # pivot and create movie-user matrix
        course_student_mat = df_study1.pivot(index='CourseID', columns='StudentID', values='StudyOrNot').fillna(0)
        # create mapper from movie title to index
        course_to_idx = {
            course: i for i, course in 
            enumerate(list(df_course.set_index('CourseID').loc[course_student_mat.index].Name)           
        )}
        # transform matrix to scipy sparse matrix
        course_student_mat_sparse = csr_matrix(course_student_mat.values)
        course_student_mat_sparse
        # %env JOBLIB_TEMP_FOLDER=/tmp
        # define model
        model_knn = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=20, n_jobs=-1)
        # fit
        model_knn.fit(course_student_mat_sparse)
        def fuzzy_matching(mapper, fav_course, verbose=True):
            match_tuple = []
            # get match
            for Name, idx in mapper.items():
                ratio = fuzz.ratio(Name.lower(), fav_course.lower())
                if ratio >= 60:
                    match_tuple.append((Name, idx, ratio))
            # sort
            match_tuple = sorted(match_tuple, key=lambda x: x[2])[::-1]
            return match_tuple[0][1]

        recommend_list = []
        def make_recommendation(model_knn, data, mapper, fav_course, n_recommendations):
            # fit
            model_knn.fit(data)
            # get input movie index
            print(fav_course+' '+'được user click vào!')
            print("\n")
            idx = fuzzy_matching(mapper, fav_course, verbose=True)
            # inference
            distances, indices = model_knn.kneighbors(data[idx], n_neighbors=n_recommendations+1)
            # get list of raw idx of recommendations
            raw_recommends = \
                sorted(list(zip(indices.squeeze().tolist(), distances.squeeze().tolist())), key=lambda x: x[1])[:0:-1]
            # get reverse mapper
            reverse_mapper = {v: k for k, v in mapper.items()}
            # List sort base on second element
            def take_second(elem):
                return elem[1]
            raw_recommends1 = sorted(raw_recommends,key=take_second)
            print('Các môn học tự chọn nhóm 1 bạn nên học vào kỳ sau :')
            for i, (idx, dist) in enumerate(raw_recommends1):
                print('{0}: {1}'.format(i+1, reverse_mapper[idx]))
                recommend_list.append(reverse_mapper[idx])
            print(recommend_list)
        my_course = 'Những môn chính học kỳ'+' '+Semester
        if Major == "kythuatphanmem" and Semester == 7:
            n_recommendation = 2
        else:   
            n_recommendation = 1    
        make_recommendation(
        model_knn=model_knn,
        data=course_student_mat_sparse,
        fav_course=my_course,
        mapper=course_to_idx,
        n_recommendations=n_recommendation)
        globals()[f'obj0'] ={"Name" : recommend_list[0],"Code":df_course.loc[df_course['Name'] == recommend_list[0], 'Code'].iloc[0],"Url":df_course.loc[df_course['Name'] == recommend_list[0], 'Url'].iloc[0]}
    ######### Xong lần nhóm 1
    ######### Tự chọn nhóm 2
    if 2 in df_study.Group.values:
        print("\n")
        df_study1 = df_study.loc[(df_study.Name == 'Những môn chính học kỳ' +' '+Semester) | ((df_study.Semester == int(Semester) + 1) & (df_study.Group != 0) & (df_study.Group == 2))]
        df_study_tmp = pd.DataFrame(df_study1.groupby('StudyOrNot').size(), columns=['Count'])
        df_course_cnt = pd.DataFrame(df_study1.groupby('CourseID').size(), columns=['count'])
        #filter data
        popularity_thres = 3
        popular_course = list(set(df_course_cnt.query('count >= @popularity_thres').index))
        df_study_drop_course = df_study1[df_study1.CourseID.isin(popular_course)]
        df_study_cnt = pd.DataFrame(df_study_drop_course.groupby('CourseID').size(), columns=['count'])
        # filter data
        study_thres = 3
        active_student = list(set(df_study_cnt.query('count >= @study_thres').index))
        df_study_drop_student = df_study_drop_course[df_study_drop_course.StudentID.isin(active_student)]
        # pivot and create movie-user matrix
        course_student_mat = df_study1.pivot(index='CourseID', columns='StudentID', values='StudyOrNot').fillna(0)
        # create mapper from movie title to index
        course_to_idx = {
            course: i for i, course in 
            enumerate(list(df_course.set_index('CourseID').loc[course_student_mat.index].Name)           
    )}
        # transform matrix to scipy sparse matrix
        course_student_mat_sparse = csr_matrix(course_student_mat.values)
        course_student_mat_sparse
        # %env JOBLIB_TEMP_FOLDER=/tmp
        # define model
        model_knn = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=20, n_jobs=-1)
        # fit
        model_knn.fit(course_student_mat_sparse)
        def fuzzy_matching(mapper, fav_course, verbose=True):
            match_tuple = []
            # get match
            for Name, idx in mapper.items():
                ratio = fuzz.ratio(Name.lower(), fav_course.lower())
                if ratio >= 60:
                    match_tuple.append((Name, idx, ratio))
            # sort
            match_tuple = sorted(match_tuple, key=lambda x: x[2])[::-1]
            return match_tuple[0][1]

        recommend_list = []
        def make_recommendation(model_knn, data, mapper, fav_course, n_recommendations):
            # fit
            model_knn.fit(data)
            # get input movie index
            idx = fuzzy_matching(mapper, fav_course, verbose=True)
            # inference
            distances, indices = model_knn.kneighbors(data[idx], n_neighbors=n_recommendations+1)
            # get list of raw idx of recommendations
            raw_recommends = \
                sorted(list(zip(indices.squeeze().tolist(), distances.squeeze().tolist())), key=lambda x: x[1])[:0:-1]
            # get reverse mapper
            reverse_mapper = {v: k for k, v in mapper.items()}
            # List sort base on second element
            def take_second(elem):
                return elem[1]
            raw_recommends2 = sorted(raw_recommends,key=take_second)
            print('Các môn học tự chọn nhóm 2 bạn nên học vào kỳ sau :')
            for i, (idx, dist) in enumerate(raw_recommends2):
                print('{0}: {1}'.format(i+1, reverse_mapper[idx]))
                recommend_list.append(reverse_mapper[idx])
            print(recommend_list)
        my_course = 'Những môn chính học kỳ'+' '+Semester
        make_recommendation(
        model_knn=model_knn,
        data=course_student_mat_sparse,
        fav_course=my_course,
        mapper=course_to_idx,
        n_recommendations=1)
        globals()[f'obj1'] ={"Name" : recommend_list[0],"Code":df_course.loc[df_course['Name'] == recommend_list[0], 'Code'].iloc[0],"Url":df_course.loc[df_course['Name'] == recommend_list[0], 'Url'].iloc[0]}
        # Trả về mã khóa học : CourseID
        # globals()[f'obj1'] ={"Name" : df_course.loc[df_course['Name'] == recommend_list[0], 'CourseID'].iloc[0],"url":df_course.loc[df_course['Name'] == recommend_list[0], 'Url'].iloc[0]}
    ######### Xong lần nhóm 2
    
    if 3 in df_study.Group.values:
        print("\n")
        df_study1 = df_study.loc[(df_study.Name == 'Những môn chính học kỳ' +' '+Semester) | ((df_study.Semester == int(Semester) + 1) & (df_study.Group != 0) & (df_study.Group == 3))]
        df_study_tmp = pd.DataFrame(df_study1.groupby('StudyOrNot').size(), columns=['Count'])
        df_course_cnt = pd.DataFrame(df_study1.groupby('CourseID').size(), columns=['count'])
        #filter data
        popularity_thres = 3
        popular_course = list(set(df_course_cnt.query('count >= @popularity_thres').index))
        df_study_drop_course = df_study1[df_study1.CourseID.isin(popular_course)]
        df_study_cnt = pd.DataFrame(df_study_drop_course.groupby('CourseID').size(), columns=['count'])
        # filter data
        study_thres = 3
        active_student = list(set(df_study_cnt.query('count >= @study_thres').index))
        df_study_drop_student = df_study_drop_course[df_study_drop_course.StudentID.isin(active_student)]
        # pivot and create movie-user matrix
        course_student_mat = df_study1.pivot(index='CourseID', columns='StudentID', values='StudyOrNot').fillna(0)
        # create mapper from movie title to index
        course_to_idx = {
            course: i for i, course in 
            enumerate(list(df_course.set_index('CourseID').loc[course_student_mat.index].Name)           
        )}
        # transform matrix to scipy sparse matrix
        course_student_mat_sparse = csr_matrix(course_student_mat.values)
        course_student_mat_sparse
        # %env JOBLIB_TEMP_FOLDER=/tmp
        # define model
        model_knn = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=20, n_jobs=-1)
        # fit
        model_knn.fit(course_student_mat_sparse)
        def fuzzy_matching(mapper, fav_course, verbose=True):
            match_tuple = []
            # get match
            for Name, idx in mapper.items():
                ratio = fuzz.ratio(Name.lower(), fav_course.lower())
                if ratio >= 60:
                    match_tuple.append((Name, idx, ratio))
            # sort
            match_tuple = sorted(match_tuple, key=lambda x: x[2])[::-1]
            return match_tuple[0][1]

        recommend_list = []
        def make_recommendation(model_knn, data, mapper, fav_course, n_recommendations):
            # fit
            model_knn.fit(data)
            # get input movie index
            idx = fuzzy_matching(mapper, fav_course, verbose=True)
            # inference
            distances, indices = model_knn.kneighbors(data[idx], n_neighbors=n_recommendations+1)
            # get list of raw idx of recommendations
            raw_recommends = \
                sorted(list(zip(indices.squeeze().tolist(), distances.squeeze().tolist())), key=lambda x: x[1])[:0:-1]
            # get reverse mapper
            reverse_mapper = {v: k for k, v in mapper.items()}
            # List sort base on second element
            def take_second(elem):
                return elem[1]
            raw_recommends2 = sorted(raw_recommends,key=take_second)
            print('Các môn học tự chọn nhóm 3 bạn nên học vào kỳ sau :')
            for i, (idx, dist) in enumerate(raw_recommends2):
                print('{0}: {1}'.format(i+1, reverse_mapper[idx]))
                recommend_list.append(reverse_mapper[idx])
            print(recommend_list)
        my_course = 'Những môn chính học kỳ'+' '+Semester
        make_recommendation(
        model_knn=model_knn,
        data=course_student_mat_sparse,
        fav_course=my_course,
        mapper=course_to_idx,
        n_recommendations=1)
        globals()[f'obj2'] ={"Name" : recommend_list[0],"Code":df_course.loc[df_course['Name'] == recommend_list[0], 'Code'].iloc[0],"Url":df_course.loc[df_course['Name'] == recommend_list[0], 'Url'].iloc[0]}
    ######### Xong

    print("\nCác obj trả về")
    if 3 in df_study.Group.values:    
        if 'obj0' and 'obj1' and 'obj2' in globals() :
            print(obj0,obj1,obj2)
            return obj0, obj1, obj2
    elif 2 in df_study.Group.values:    
        if 'obj0' and 'obj1' in globals():
            print(obj0,obj1)
            return obj0, obj1
    else:
        print(obj0)
        return obj0

class Index(APIView):
    def get(self, request):
        Major = request.GET['Major']
        Semester = request.GET['Semester']
        data = Model(Major,Semester)
        if data == None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data=data, status=status.HTTP_200_OK)
