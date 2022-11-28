##############################################################
# CLTV Prediction with BG-NBD and Gamma-Gamma
################################################ ############

################################################ ###############
# Business Problem
###############################################################
# FLO wants to set a roadmap for sales and marketing activities.
# In order for the company to make a medium-long-term plan, it is necessary to estimate the potential value that existing customers will provide to the company in the future.


################################################ ###############
# Dataset Story
################################################ ###############

# The dataset consists of information obtained from the past shopping behaviors of customers who made their
# last purchases as OmniChannel (both online and offline shopper) in 2020 - 2021.

# master_id: Unique client number
# order_channel : Which channel of the shopping platform is used (Android, ios, Desktop, Mobile, Offline)
# last_order_channel : The channel where the last purchase was made
# first_order_date : The date of the customer's first purchase
# last_order_date : The date of the last purchase made by the customer
# last_order_date_online : The date of the last purchase made by the customer on the online platform
# last_order_date_offline : The date of the last purchase made by the customer on the offline platform
# order_num_total_ever_online : The total number of purchases made by the customer on the online platform
# order_num_total_ever_offline : Total number of purchases made by the customer offline
# customer_value_total_ever_offline : The total price paid by the customer for offline purchases
# customer_value_total_ever_online : The total price paid by the customer for their online shopping
# interested_in_categories_12 : List of categories the customer has purchased from in the last 12 months


################################################ ###############
# TASKS
################################################ ###############
# TASK 1: Preparing the Data
           # 1. Read the data flo_data_20K.csv. Make a copy of the dataframe.
           #2. Define the outlier_thresholds and replace_with_thresholds functions needed to suppress outliers.
           # Note: When calculating cltv, frequency values must be integers. Therefore, round the lower and upper limits with round().
           # 3. Set the variables "order_num_total_ever_online","order_num_total_ever_offline","customer_value_total_ever_offline","customer_value_total_ever_online"
           # suppress outliers if any.
           # 4. Omnichannel means that customers shop from both online and offline platforms. Total for each customer
           # create new variables for number of purchases and spend.
           # 5. Examine the variable types. Change the type of variables that express date to date.

# TASK 2: Creating CLTV Data Structure
           # 1. Take 2 days after the date of the last purchase in the data set as the date of analysis.
           # 2. Create a new cltv dataframe with customer_id, recency_cltv_weekly, T_weekly, frequency and monetary_cltv_avg values.
           # Monetary value will be expressed as average value per purchase, recency and tenure values will be expressed in weekly terms.


# TASK 3: BG/NBD, Establishing Gamma-Gamma Models, Calculating CLTV
           # 1. Fit the BG/NBD model.
                # a. Estimate expected purchases from customers in 3 months and add exp_sales_3_month to cltv dataframe.
                # b. Estimate expected purchases from customers in 6 months and add exp_sales_6_month to cltv dataframe.
           # 2. Fit the Gamma-Gamma model. Estimate the average value of the customers and add it to the cltv dataframe as exp_average_value.
           # 3. Calculate 6 months CLTV and add it to the dataframe with the name cltv.
                # a. Standardize the cltv values you calculated and create the scaled_cltv variable.
                # b. Observe the 20 people with the highest Cltv value.

# TASK 4: Creating Segments by CLTV
           # 1. Divide all your customers into 4 groups (segments) according to the 6-month standardized CLTV and add the group names to the dataset. Add it to the dataframe with the name cltv_segment.
           # 2. Make short 6-month action suggestions to the management for 2 groups you will choose from among 4 groups.

# TASK 5: Functionalize the whole process.


################################################ ###############
# TASK 1: Preparing the Data
################################################ ###############


import pandas as pd
import datetime as dt
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from sklearn.preprocessing import MinMaxScaler
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.2f' % x)
pd.options.mode.chained_assignment = None

# 1. Read the OmniChannel.csv data. Make a copy of the dataframe.
df_ = pd.read_csv("datasets/flo_data_20K.csv")
df = df_.copy()

#2. Define the outlier_thresholds and replace_with_thresholds functions needed to suppress outliers.
# Note: When calculating cltv, frequency values must be integers. Therefore, round the lower and upper limits with round().
def outlier_thresholds(dataframe, variable):
    quartile1 = dataframe[variable].quantile(0.01)
    quartile3 = dataframe[variable].quantile(0.99)
    interquantile_range = quartile3 - quartile1
    up_limit = quartile3 + 1.5 * interquantile_range
    low_limit = quartile1 - 1.5 * interquantile_range
    return low_limit, up_limit

def replace_with_thresholds(dataframe, variable):
    low_limit, up_limit = outlier_thresholds(dataframe, variable)
    dataframe.loc[(dataframe[variable] < low_limit), variable] = round(low_limit,0)
    dataframe.loc[(dataframe[variable] > up_limit), variable] = round(up_limit,0)


# 3. If the variables "order_num_total_ever_online","order_num_total_ever_offline","customer_value_total_ever_offline",
# "customer_value_total_ever_online" have outliers, we suppress them.
columns = ["order_num_total_ever_online", "order_num_total_ever_offline", "customer_value_total_ever_offline","customer_value_total_ever_online"]
for col in columns:
    replace_with_thresholds(df, col)


# 4. Omnichannel means that customers shop from both online and offline platforms.
# Create new variables for each customer's total purchases and spending.
df["order_num_total"] = df["order_num_total_ever_online"] + df["order_num_total_ever_offline"]
df["customer_value_total"] = df["customer_value_total_ever_offline"] + df["customer_value_total_ever_online"]

# 5. Examine the variable types. Change the type of variables that express date to date.
date_columns = df.columns[df.columns.str.contains("date")]
df[date_columns] = df[date_columns].apply(pd.to_datetime)

################################################ ###############
# TASK 2: Creating CLTV Data Structure
################################################ ###############

# 1. Take 2 days after the date of the last purchase in the data set as the date of analysis.
df["last_order_date"].max() # 2021-05-30
analysis_date = dt.datetime(2021,6,1)


# 2.Create a new cltv dataframe with customer_id, recency_cltv_weekly, T_weekly, frequency and monetary_cltv_avg values.
cltv_df = pd.DataFrame()
cltv_df["customer_id"] = df["master_id"]
cltv_df["recency_cltv_weekly"] = ((df["last_order_date"]- df["first_order_date"]).astype('timedelta64[D]')) / 7
cltv_df["T_weekly"] = ((analysis_date - df["first_order_date"]).astype('timedelta64[D]'))/7
cltv_df["frequency"] = df["order_num_total"]
cltv_df["monetary_cltv_avg"] = df["customer_value_total"] / df["order_num_total"]

cltv_df.head()

################################################ ###############
# TASK 3: BG/NBD, Establishing Gamma-Gamma Models, calculating 6-month CLTV
################################################ ###############

# 1. Install BG/NBD model.
bgf = BetaGeoFitter(penalizer_coef=0.001)
bgf.fit(cltv_df['frequency'],
        cltv_df['recency_cltv_weekly'],
        cltv_df['T_weekly'])

# Estimate expected purchases from customers in 3 months and add exp_sales_3_month to cltv dataframe.
cltv_df["exp_sales_3_month"] = bgf.predict(4*3,
                                        cltv_df['frequency'],
                                        cltv_df['recency_cltv_weekly'],
                                        cltv_df['T_weekly'])

# Estimate expected purchases from customers in 6 months and add exp_sales_6_month to cltv dataframe.
cltv_df["exp_sales_6_month"] = bgf.predict(4*6,
                                       cltv_df['frequency'],
                                       cltv_df['recency_cltv_weekly'],
                                       cltv_df['T_weekly'])

# Let's review the 10 people who will make the most purchases in the 3rd and 6th months. Is there a difference?
cltv_df.sort_values("exp_sales_3_month",ascending=False)[:10]

cltv_df.sort_values("exp_sales_6_month",ascending=False)[:10]


# 2.  Fit the Gamma-Gamma model. Estimate the average value of the customers and add it to the cltv dataframe as exp_average_value.
ggf = GammaGammaFitter(penalizer_coef=0.01)
ggf.fit(cltv_df['frequency'], cltv_df['monetary_cltv_avg'])
cltv_df["exp_average_value"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                                                cltv_df['monetary_cltv_avg'])
cltv_df.head()

# 3. Calculate 6 months CLTV and add it to the dataframe with the name cltv.
cltv = ggf.customer_lifetime_value(bgf,
                                   cltv_df['frequency'],
                                   cltv_df['recency_cltv_weekly'],
                                   cltv_df['T_weekly'],
                                   cltv_df['monetary_cltv_avg'],
                                   time=6,
                                   freq="W",
                                   discount_rate=0.01)
cltv_df["cltv"] = cltv



# Observe the 20 people with the highest CLTV value.
cltv_df.sort_values("cltv",ascending=False)[:20]

################################################ ###############
# TASK 4: Creating Segments by CLTV
################################################ ###############

# 1. Divide all your customers into 4 groups (segments) according to the 6-month standardized CLTV and add the group names to the dataset.
# Assign with the name cltv_segment.
cltv_df["cltv_segment"] = pd.qcut(cltv_df["cltv"], 4, labels=["D", "C", "B", "A"])
cltv_df.head()

################################################ ###############
# BONUS: Streamline the entire process.
################################################ ###############

def create_cltv_df(dataframe):

    # Preparing Data
    columns = ["order_num_total_ever_online", "order_num_total_ever_offline", "customer_value_total_ever_offline","customer_value_total_ever_online"]
    for col in columns:
        replace_with_thresholds(dataframe, col)

    dataframe["order_num_total"] = dataframe["order_num_total_ever_online"] + dataframe["order_num_total_ever_offline"]
    dataframe["customer_value_total"] = dataframe["customer_value_total_ever_offline"] + dataframe["customer_value_total_ever_online"]
    dataframe = dataframe[~(dataframe["customer_value_total"] == 0) | (dataframe["order_num_total"] == 0)]
    date_columns = dataframe.columns[dataframe.columns.str.contains("date")]
    dataframe[date_columns] = dataframe[date_columns].apply(pd.to_datetime)

    # Creation of CLTV data structure
    dataframe["last_order_date"].max()  # 2021-05-30
    analysis_date = dt.datetime(2021, 6, 1)
    cltv_df = pd.DataFrame()
    cltv_df["customer_id"] = dataframe["master_id"]
    cltv_df["recency_cltv_weekly"] = ((dataframe["last_order_date"] - dataframe["first_order_date"]).astype('timedelta64[D]')) / 7
    cltv_df["T_weekly"] = ((analysis_date - dataframe["first_order_date"]).astype('timedelta64[D]')) / 7
    cltv_df["frequency"] = dataframe["order_num_total"]
    cltv_df["monetary_cltv_avg"] = dataframe["customer_value_total"] / dataframe["order_num_total"]
    cltv_df = cltv_df[(cltv_df['frequency'] > 1)]

    # Establishment of BG-NBD Model
    bgf = BetaGeoFitter(penalizer_coef=0.001)
    bgf.fit(cltv_df['frequency'],
            cltv_df['recency_cltv_weekly'],
            cltv_df['T_weekly'])
    cltv_df["exp_sales_3_month"] = bgf.predict(4 * 3,
                                               cltv_df['frequency'],
                                               cltv_df['recency_cltv_weekly'],
                                               cltv_df['T_weekly'])
    cltv_df["exp_sales_6_month"] = bgf.predict(4 * 6,
                                               cltv_df['frequency'],
                                               cltv_df['recency_cltv_weekly'],
                                               cltv_df['T_weekly'])

    # # Establishing the Gamma-Gamma Model
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(cltv_df['frequency'], cltv_df['monetary_cltv_avg'])
    cltv_df["exp_average_value"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                                                           cltv_df['monetary_cltv_avg'])

    # cltv forecast
    cltv = ggf.customer_lifetime_value(bgf,
                                       cltv_df['frequency'],
                                       cltv_df['recency_cltv_weekly'],
                                       cltv_df['T_weekly'],
                                       cltv_df['monetary_cltv_avg'],
                                       time=6,
                                       freq="W",
                                       discount_rate=0.01)
    cltv_df["cltv"] = cltv

    # CLTV segmentation
    cltv_df["cltv_segment"] = pd.qcut(cltv_df["cltv"], 4, labels=["D", "C", "B", "A"])

    return cltv_df

cltv_df = create_cltv_df(df)


cltv_df.head(10)


