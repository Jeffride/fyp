import re
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import seaborn as sns
from flask_mysqldb import MySQL
from flask import Flask
app = Flask(__name__)


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'xmasbarnicleant;l0ps'
app.config['MYSQL_DB'] = 'ai'

mysql = MySQL(app)


'''
TO DO:
- Read in the test set from the mysql database
- Use this test set to make predictions
'''


def init():
    pairwise_data = pd.read_csv('pairwise_bin.csv')

    pairwise_data = pairwise_data.drop_duplicates()

    pairwise_data
    # Shuffle the dataset
    pairwise_data = pairwise_data.sample(frac=1, random_state=2)
    pairwise_data.reset_index(drop=True, inplace=True)
    return pairwise_data

def similarityWeighting(u,v):
    P = 0
    Q = 0
    for pairs,pairs1 in zip(u.values,v.values):
        if ((pairs[1] == pairs1[1]) and (pairs[2] == pairs1[2])):
            if (pairs[3] >=0 ) and (pairs1[3] >= 0):
                print("similar pair found: "+str(pairs)+" & "+str(pairs1))
                P+=1
                continue
            elif (pairs[3] >=0 ) and (pairs1[3] < 0):
                print("non similar pair found: "+str(pairs)+" & "+str(pairs1))
                Q+=1
                continue
            elif (pairs[3] <0 ) and (pairs1[3] >= 0):
                print("non similar pair found: "+str(pairs)+" & "+str(pairs1))
                Q+=1
                continue
        if ((pairs[2] == pairs1[1]) and (pairs[1] == pairs1[2])):
            if (pairs[3] >=0 ) and (pairs1[3] < 0):
                print("similar pair found: "+str(pairs)+" & "+str(pairs1))
                P+=1
                continue
            elif (pairs[3] <0) and (pairs1[3] >= 0):
                print("similar pair found: "+str(pairs)+" & "+str(pairs1))
                P+=1
                continue
            elif (pairs[3] >=0) and (pairs1[3] >=0):
                print("non similar pair found: "+str(pairs)+" & "+str(pairs1))
                Q+=1
                continue
            elif (pairs[3] <0) and (pairs1[3] <0):
                print("non similar pair found: "+str(pairs)+" & "+str(pairs1))
                Q+=1
                continue
    if P+Q!=0:
        return (P-Q)/(P+Q)
    return 0

def predict_missing_pairscores(user_profile,test_set,train_set):  
    x = 0
#     for movie_i, movie_j in test_set[['i','j']].values:
    results =[]
    movies = []
    for row in test_set.values:
        score = 999
        #create a df which contains the target movie pair
        df = train_set[((train_set['i']==row[1])&(train_set['j']==row[2]))|((train_set['j']==row[1])|(train_set['i']==row[2]))] 
        if df.shape[0] > 0:
            df = df.drop_duplicates(subset=['userId'], keep= 'first')
#             users = df[df['userId'].unique()]
            sum_scores = 0.0
            sum_sims = 0.0
            #go through all users who have rated the target movie pair
            for u in df.values: 
                #THE PROBLEM HERE IS USERID ARE BEING PASSED INTO SIM FUNCTION MULTIPLE TIMES
                if u[0] != row[0]:
                    sim_score = similarityWeighting(user_profile,train_set[train_set['userId'] == u[0]])
#                    sim_score = sim(user_profile,train_set[train_set['userId'] == u[0]])
                    rating = u[3]
                    sum_sims += sim_score
                    sum_scores += sim_score*rating
        
            if sum_sims != 0.0:
                print("sim score found")
                score = np.round(sum_scores / sum_sims)
                score = -1 if score <= -1 else 1 if score >= 1 else 1
        results += [[row[0],row[1],row[2],score]]
        movies += row[1]
        movies += row[2]
    return results,movies

def selectedMovies(results):
    m_list = []
    for row in results:
        if row[3] == 1:
            m_list += [row[1]]
        elif row[3] == -1:
            m_list += [row[2]]
    return m_list

def personalised_ranking(user_profile,movies,train_set):
    i = list(train_set['i'].unique())
    ranking = []
    for m in movies:
        avg = 0
        test_set = []
        for m1 in i:
            test_set += [[10,m,m1,999]]
        #compute pairscore for m and all other movies in train_Set
        df = pd.DataFrame(data = test_set, columns= ['userId','i','j','score'])
        r = predict_missing_pairscores(user_profile,df,train_set)
        df1 = pd.DataFrame(data = r,columns= ['userId','i','j','score'])
        df1 = df1[df1['score'] != 999] 
        if df1.shape[0]>0:
            avg = (df1['score'].sum())/(df1.shape[0])
        ranking += [m,avg]
    return ranking

# def generateMovie(df,movies):
#     sim_best = 0.0
#     sim_user = None
#     result = None

#     for r in df.values:
#         movie_i = r[1]
#         movie_j = r[2]
#         choice = r[3]
#         choice_inv = 1 - choice
# #         df1 = movies[((movies['i']==movie_i)&(movies['j']==movie_i)&(movies['score']==choice))|((movies['i']==movie_i)&(movies['j']==movie_j)&(movies['score']==choice_inv))]
#         df1 = movies[((movies['i']==movie_i)&(movies['score']==choice))|((movies['j']==movie_j)&(movies['score']==choice))] 
#         if df1.shape[0] > 0:

#             for u in df1.values:
#                 user_profile = movies[movies['userId'] == u[0]]

# #                 sim = binsimilarityWeighting(user_profile,df)
#                 sim = simWeighting1(user_profile,df)
#                 if sim > sim_best:
#                     sim_best = sim
#                     sim_user = (u[0],sim)
#         else:
#             continue
#     if sim_user != None:
#         cursor = mysql.connection.cursor()
#         cursor.execute('''select movieId from ai.ratings where userId = '''+str(sim_user[0])+''' order by rating desc limit 5''')
#         mysql.connection.commit()
#          # result = cursor.fetchall()[0][1]
#         result = [item[0] for item in cursor.fetchall()]
#         result = tuple(result)
#         print("RESULT")
#         print(result)

#         #Here I take the top 5 rated movies from neighbour and translate into imdb ids where i then choose the most recent movie
#         cursor = mysql.connection.cursor()
#         cursor.execute('''SELECT imdbId FROM ai.links WHERE movieId IN '''+str(result)+'''order by imdbId desc''')
#         mysql.connection.commit()
#         result = str(cursor.fetchone()[0])
#         cursor.close()
#     return result

# def generateMovie(df,movies):
#     sim = ""
#     sim_user = None
#     result = None
#     for r in df.values:
#         movie_i = r[1]
#         movie_j = r[2]
#         score = r[3]
#         df1 = movies[((movies['i']==movie_i)&(movies['score']==score))|((movies['j']==movie_j)&(movies['score']==score))] 
#         print(df1)
#         if df1.shape[0] > 0:
#             for u in df1.values:
#                 user_profile = movies[movies['userId'] == u[0]]
#                 sim = binsimilarityWeighting(user_profile,df)
#                 if sim>0.0:
#                     sim_user = u[0]
#                     cursor = mysql.connection.cursor()
#                     cursor.execute('''select * from ai.ratings where userId = '''+str(sim_user)+''' order by rating desc limit 5''')
#                     mysql.connection.commit()
#                     result = cursor.fetchall()[0][1]
#                     cursor = mysql.connection.cursor()
#                     cursor.execute('''SELECT imdbId FROM ai.links WHERE movieId = '''+str(result))
#                     mysql.connection.commit()
#                     result = str(cursor.fetchone()[0])
#                     cursor.close()
#                     break
#                 #calculate similarity of two users and store in data structure
#         else:
#             continue
#     return result
    '''
    Input: df which contains users choices
    Find users who have seen any of the user choices
    For such users
        Find most similar neighbour
    Find that neighbourds fave film
    return this film
    '''
