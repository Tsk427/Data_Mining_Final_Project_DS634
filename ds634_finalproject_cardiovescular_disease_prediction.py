# -*- coding: utf-8 -*-
"""DS634_FinalProject_Cardiovescular_Disease_Prediction.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1cJTGxLaXO2fo8C0qTVCqLoCz86T_AsNs

### Importing all the Libraries
"""

import numpy as np
import pandas as pd
import joblib
import warnings
import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import  accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_curve, auc

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

"""### Importing the dataset"""

df = pd.read_csv('dataset/health_data.csv')

df.head()

df.info()

"""### Checking missing values"""

print(df.isnull().sum())

null_rows = df[df.isnull().any(axis=1)]
print("Rows with null values:")
print(null_rows)

#drop id
df = df.drop(['id', 'Unnamed: 0'], axis=1)

"""### Removing Outliers:
It is important to remove outliers to improve the performance of our prediction models. We have removed outliers that fall outside the range of 2.5% to 97.5% in all instances of ap_hi, ap_lo, weight, and height features. This process has decreased the entries in the data set from 70,000 to 60,142 records.
"""

df.drop(df[(df['height'] > df['height'].quantile(0.975)) | (df['height'] < df['height'].quantile(0.025))].index,inplace=True)
df.drop(df[(df['weight'] > df['weight'].quantile(0.975)) | (df['weight'] < df['weight'].quantile(0.025))].index,inplace=True)
df.drop(df[(df['ap_hi'] > df['ap_hi'].quantile(0.975)) | (df['ap_hi'] < df['ap_hi'].quantile(0.025))].index,inplace=True)
df.drop(df[(df['ap_lo'] > df['ap_lo'].quantile(0.975)) | (df['ap_lo'] < df['ap_lo'].quantile(0.025))].index,inplace=True)
len(df)

#Cases where diastolic pressure is higher than systolic
df[df['ap_lo']> df['ap_hi']].shape[0]

df.describe()

"""### Data Processing and cleaning"""

df['age'] = (df['age'] / 365).round().astype('int') #Converting age from days to years

print(df.head())

# # Define the bin edges and labels
age_edges = [30, 35, 40, 45, 50, 55, 60, 65]
age_labels = [0, 1, 2, 3, 4, 5, 6]

#  bin in  5 years span
df['age_group'] = pd.cut(df['age'], bins=7, labels=range(7), include_lowest=True,right=True)
df.head()

df['bmi'] = df['weight']/((df['height']/100)**2)
df.head()

bmiMin = int(df['bmi'].min())
bmiMax = int(df['bmi'].max())

print(bmiMin, bmiMax)

df['bmi'] = pd.cut(df['bmi'], bins=6, labels=range(6), right=True, include_lowest=True)

df.head()


df["bmi"].value_counts(normalize=True)

df['map'] = ((2* df['ap_lo']) + df['ap_hi']) / 3

mapMin = int(df['map'].min())
mapMax = int(df['map'].max())

print(mapMin, mapMax)

df['map'] = pd.cut(df['map'], bins=6, labels=range(6), right=True, include_lowest=True)

df.head()

df_og=df

df=df.drop(['height','weight','ap_hi','ap_lo','age'],axis=1)

df.head()

le = LabelEncoder()
df = df.apply(le.fit_transform)
df.describe()

# Set up figure
plt.figure(figsize=(10, 8))

# Draw correlation matrix
sns.heatmap(df.corr(), annot=True, cmap='Spectral', fmt=".2f", linewidths=.5)

# Show the figure
plt.title('Correlation Matrix')
plt.show()

cardio_0 = df[df['cardio'] == 0].sample(n=5000, random_state=42)
cardio_1 = df[df['cardio'] == 1].sample(n=5000, random_state=42)

# Concatenate the sliced dataframes
data = pd.concat([cardio_0, cardio_1])

# Shuffle the data to mix 0s and 1s
data = data.sample(frac=1, random_state=42).reset_index(drop=True)
data.shape

x = data.drop(['cardio','gender','alco'], axis=1)
y = data['cardio']

x.head()

"""### Splitting the dataset into train and test"""

x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.20,random_state=1)

x_train.info()

"""### Function to calculate performance metrics"""

def calc_metrics(confusion_matrix):
    TP, FN = confusion_matrix[0][0], confusion_matrix[0][1]
    FP, TN = confusion_matrix[1][0], confusion_matrix[1][1]
    TPR = TP / (TP + FN)
    TNR = TN / (TN + FP)
    FPR = FP / (TN + FP)
    FNR = FN / (TP + FN)
    Precision = TP / (TP + FP)
    F1_measure = 2 * TP / (2 * TP + FP + FN)
    Accuracy = (TP + TN) / (TP + FP + FN + TN)
    Error_rate = (FP + FN) / (TP + FP + FN + TN)
    BACC = (TPR + TNR) / 2
    TSS = TPR - FPR
    HSS = 2 * (TP * TN - FP * FN) / ((TP + FN) * (FN + TN) + (TP + FP) * (FP + TN))
    metrics = [TP, TN, FP, FN, TPR, TNR, FPR, FNR, Precision, F1_measure, Accuracy, Error_rate, BACC, TSS, HSS]
    return metrics

import numpy as np
from sklearn.metrics import confusion_matrix, brier_score_loss, roc_auc_score

def get_metrics(model, X_train, X_test, y_train, y_test, LSTM_flag):
    metrics = []

    if LSTM_flag == 1:
        # Convert data to numpy array
        Xtrain, Xtest, ytrain, ytest = map(np.array, [X_train, X_test, y_train, y_test])
        # Reshape data
        shape = Xtrain.shape
        Xtrain_reshaped = Xtrain.reshape(len(Xtrain), shape[1], 1)
        Xtest_reshaped = Xtest.reshape(len(Xtest), shape[1], 1)
        model.fit(Xtrain_reshaped, ytrain, epochs=50, validation_data=(Xtest_reshaped, ytest), verbose=0)
        lstm_scores = model.evaluate(Xtest_reshaped, ytest, verbose=0)
        predict_prob = model.predict(Xtest_reshaped)
        pred_labels = predict_prob > 0.5
        pred_labels_1 = pred_labels.astype(int)
        matrix = confusion_matrix(ytest, pred_labels_1, labels=[1, 0])
        lstm_brier_score = brier_score_loss(ytest, predict_prob)
        lstm_roc_auc = roc_auc_score(ytest, predict_prob)
        metrics.extend(calc_metrics(matrix))
        metrics.extend([lstm_brier_score, lstm_roc_auc, lstm_scores[1]])

    elif LSTM_flag == 0:
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        matrix = confusion_matrix(y_test, predicted, labels=[1, 0])
        model_brier_score = brier_score_loss(y_test, model.predict_proba(X_test)[:, 1])
        model_roc_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        metrics.extend(calc_metrics(matrix))
        metrics.extend([model_brier_score, model_roc_auc, model.score(X_test, y_test)])

    return metrics

"""## Finding best parameters for Random Forest model"""

# build the model
rfModel = RandomForestClassifier(random_state=42)

# Fit the model
rfModel.fit(x_train, y_train)

# Make predictions
rf_pred = rfModel.predict(x_test)

# accuracy
rf_accuracy = accuracy_score(y_test, rf_pred)*100
print(f"Accuracy without CV: {rf_accuracy:.2f}")

param_grid = {
    'n_estimators': [100, 200, 300, 500],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10, 20],
    'max_features': ['sqrt', 'log2', None],
}

# Create grid search
rf_gridsearch = GridSearchCV(estimator=rfModel,param_grid=param_grid, cv=10, scoring='accuracy',n_jobs=-1)

# Fit grid search
rf_gridsearch.fit(x_train, y_train)

rf_best_params = rf_gridsearch.best_params_
best_estimator = rf_gridsearch.best_estimator_

print(f"Best Parameters : {rf_best_params}")
print(f"Best Estimator  : {best_estimator}")

max_depth = rf_gridsearch.best_params_['max_depth']
min_samples_split = rf_gridsearch.best_params_['min_samples_split']
n_estimators = rf_gridsearch.best_params_['n_estimators']

rf_pred_CV = best_estimator.predict(x_test)

rf_accuracy_cv = accuracy_score(y_test, rf_pred_CV)*100
print(f"Best Accuracy: {rf_accuracy_cv:.2f}")

print(f"Random Forest accuracy without CV : {rf_accuracy:.2f}")
print(f"Random Forest accuracy with CV    : {rf_accuracy_cv:.2f}")

"""## Finding best parameters for the KNN model"""

knn_parameters = {"n_neighbors": [ 3, 4, 5, 6, 8, 10]}
# Create KNN model
knn_model = KNeighborsClassifier()
# Perform grid search with cross-validation
knn_cv = GridSearchCV(knn_model, knn_parameters, cv=10, n_jobs=-1)
knn_cv.fit(x_train, y_train)
# Print the best parameters found by GridSearchCV
print("\nBest Parameters for KNN based on GridSearchCV: ", knn_cv.best_params_)
print('\n')

best_n_neighbors = knn_cv.best_params_['n_neighbors']

"""### Using 10 fold Cross Validation"""

metric_columns = ['TP', 'TN', 'FP', 'FN', 'TPR', 'TNR', 'FPR', 'FNR', 'Precision',
                  'F1_measure', 'Accuracy', 'Error_rate', 'BACC', 'TSS', 'HSS', 'Brier_score',
                  'AUC', 'Acc_by_package_fn']

# Initialize metrics lists for each algorithm
knn_metrics_list, rf_metrics_list, lstm_metrics_list = [],[],[]

# 10 Iterations of 10-fold cross-validation
cv_stratified = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

for iter_num, (train_index, test_index) in enumerate(cv_stratified.split(x, y), start=1):
    # KNN Model
    knn_model = KNeighborsClassifier(n_neighbors=best_n_neighbors)

    # Random Forest Model
    rf_model = RandomForestClassifier(min_samples_split=min_samples_split, n_estimators=n_estimators , max_depth= max_depth)

    # LSTM model
    lstm_model = Sequential()
    lstm_model.add(LSTM(64, activation='relu', return_sequences=False))
    lstm_model.add(Dense(1, activation='sigmoid'))

    # Compile model
    lstm_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

    # Get metrics for each algorithm
    knn_metrics = get_metrics(knn_model, x_train, x_test, y_train, y_test, 0)
    rf_metrics = get_metrics(rf_model, x_train, x_test, y_train, y_test, 0)
    lstm_metrics = get_metrics(lstm_model, x_train, x_test, y_train, y_test, 1)

    # Append metrics to respective lists
    knn_metrics_list.append(knn_metrics)
    rf_metrics_list.append(rf_metrics)
    lstm_metrics_list.append(lstm_metrics)

    # Create a DataFrame for all metrics
    metrics_all_df = pd.DataFrame([knn_metrics, rf_metrics, lstm_metrics],
                                  columns=metric_columns, index=['KNN', 'RF', 'LSTM'])

    # Display metrics for all algorithms in each iteration
    print('\nIteration {}: \n'.format(iter_num))
    print('\n----- Metrics for all Algorithms in Iteration {} -----\n'.format(iter_num))
    print(metrics_all_df.round(decimals=2).T)
    print('\n')

# Initialize metric index for each iteration
metric_index_df = ['iter1', 'iter2', 'iter3', 'iter4', 'iter5', 'iter6', 'iter7', 'iter8', 'iter9', 'iter10']

# Create DataFrames for each algorithm's metrics
knn_metrics_df = pd.DataFrame(knn_metrics_list, columns=metric_columns, index=metric_index_df)
rf_metrics_df = pd.DataFrame(rf_metrics_list, columns=metric_columns, index=metric_index_df)
lstm_metrics_df = pd.DataFrame(lstm_metrics_list, columns=metric_columns, index=metric_index_df)

# Display metrics for each algorithm in each iteration
algorithm_names = ['KNN', 'RF', 'LSTM']
for i, metrics_df in enumerate([knn_metrics_df, rf_metrics_df, lstm_metrics_df], start=1):
    print('\nMetrics for Algorithm {}:\n'.format(algorithm_names[i-1]))
    print(metrics_df.round(decimals=2).T)
    print('\n')

"""### Average Result for each model"""

# Calculate the average metrics for each algorithm
knn_avg_df = knn_metrics_df.mean()
rf_avg_df = rf_metrics_df.mean()
lstm_avg_df = lstm_metrics_df.mean()
# Create a DataFrame with the average performance for each algorithm
avg_performance_df = pd.DataFrame({'KNN': knn_avg_df, 'RF': rf_avg_df, 'LSTM': lstm_avg_df}, index=metric_columns)
# Display the average performance for each algorithm
print(avg_performance_df.round(decimals=2))
print('\n')

"""### Plotting ROC-SUC Curve for all the models"""

# Train models with best parameters
best_knn_model = KNeighborsClassifier(n_neighbors= best_n_neighbors)
best_rf_model = RandomForestClassifier(n_estimators=rf_best_params['n_estimators'], min_samples_split=rf_best_params['min_samples_split'])

# Fit models
best_knn_model.fit(x_train, y_train)
best_rf_model.fit(x_train, y_train)

#lstm model
lstm_model = Sequential()
lstm_model.add(LSTM(64, activation='relu', return_sequences=False))
lstm_model.add(Dense(1, activation='sigmoid'))
lstm_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

# Convert data to numpy array
X_train_array = x_train.to_numpy()
X_test_array = x_test.to_numpy()
y_train_array = y_train.to_numpy()
y_test_array = y_test.to_numpy()

# Reshape data for LSTM model compatibility
input_shape = X_train_array.shape
input_train = X_train_array.reshape(len(X_train_array), input_shape[1], 1)
input_test = X_test_array.reshape(len(X_test_array), input_shape[1], 1)
output_train = y_train_array
output_test = y_test_array

# Train the LSTM model
history = lstm_model.fit(input_train, output_train, epochs=50, validation_data=(input_test, output_test), verbose=0)

# Predict probabilities for test set
knn_probs = best_knn_model.predict_proba(x_test)[:, 1]
rf_probs = best_rf_model.predict_proba(x_test)[:, 1]
lstm_probs = lstm_model.predict(x_test).ravel()  # Assuming lstm_model is already trained

# Calculate ROC AUC scores
knn_fpr, knn_tpr, _ = roc_curve(y_test, knn_probs)
knn_roc_auc = auc(knn_fpr, knn_tpr)

rf_fpr, rf_tpr, _ = roc_curve(y_test, rf_probs)
rf_roc_auc = auc(rf_fpr, rf_tpr)

lstm_fpr, lstm_tpr, _ = roc_curve(y_test, lstm_probs)
lstm_roc_auc = auc(lstm_fpr, lstm_tpr)

# Plot ROC AUC curves
plt.figure(figsize=(15, 5))

# KNN ROC AUC curve
plt.subplot(1, 3, 1)
plt.plot(knn_fpr, knn_tpr, color='blue', lw=2, label='KNN ROC curve (AUC = %0.2f)' % knn_roc_auc)
plt.plot([0, 1], [0, 1], color='gray', linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('KNN ROC AUC Curve')
plt.legend(loc="lower right")

# RandomForest ROC AUC curve
plt.subplot(1, 3, 2)
plt.plot(rf_fpr, rf_tpr, color='green', lw=2, label='RandomForest ROC curve (AUC = %0.2f)' % rf_roc_auc)
plt.plot([0, 1], [0, 1], color='gray', linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('RandomForest ROC AUC Curve')
plt.legend(loc="lower right")

# LSTM ROC AUC curve
plt.subplot(1, 3, 3)
plt.plot(lstm_fpr, lstm_tpr, color='red', lw=2, label='LSTM ROC curve (AUC = %0.2f)' % lstm_roc_auc)
plt.plot([0, 1], [0, 1], color='gray', linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('LSTM ROC AUC Curve')
plt.legend(loc="lower right")

plt.tight_layout()
plt.show()