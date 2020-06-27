# TD Ameritrade
import requests
# Plaid API (Simple Bank)
from plaid import Client
# Updating Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# Sending Email
import smtplib

import datetime as dt
import os
from random import choice
from dotenv import load_dotenv

load_dotenv()

runProgram = False
weekno = dt.datetime.today().weekday()

if weekno < 5:
    runProgram = True


# All Environment Variables ...
# TD
TD_REFRESH_TOKEN = os.environ.get('TD_REFRESH_TOKEN')
TD_REFRESH_URL = "https://api.tdameritrade.com/v1/oauth2/token"
TD_CLIENT_ID = os.environ.get('TD_CLIENT_ID')
TD_ACCOUNT_URL = f"https://api.tdameritrade.com/v1/accounts/{os.environ.get('TD_ACCOUNT_NUMBER')}"
TD_KEY = os.environ.get('TD_KEY')

# Simple Bank
SIMPLE_CLIENT_ID = os.environ.get('SIMPLE_CLIENT_ID')
SIMPLE_PUBLIC_KEY = os.environ.get('SIMPLE_PUBLIC_KEY')
SIMPLE_SECRET = os.environ.get('SIMPLE_SECRET')
SIMPLE_ACCESS_TOKEN = os.environ.get('SIMPLE_ACCESS_TOKEN')

# Weather API
WEATHER_KEY = os.environ.get('WEATHER_KEY')

# Email
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

# Printing String Dates
def numberToMonth(number):
    number = int(number)
    month = ''
    if number == 1:
        month = "January"
    if number == 2:
        month = "February"
    if number == 3:
        month = "March"
    if number == 4:
        month = "April"
    if number == 5:
        month = 'May'
    if number == 6:
        month = 'June'
    if number == 7:
        month = "July"
    if number == 8:
        month = "August"
    if number == 9:
        month = 'September'
    if number == 10:
        month = 'October'
    if number == 11:
        month = 'November'
    if number == 12:
        month = 'December'
    return month


# Accesses the following API's: TD Ameritrade, Simple Bank, OpenWeatherMap, and Quote of the day
# The information is updating with the google sheets api and an email is sent
class DailyEmail:
    def __init__(self):
        pass

    def getTDAmeritradeData(self):
        try:
            params = {'grant_type': 'refresh_token','refresh_token': TD_REFRESH_TOKEN,
          'client_id':TD_CLIENT_ID}
            headers = {'Content-Type':'application/x-www-form-urlencoded'}
            response = requests.post(TD_REFRESH_URL,data=params,headers=headers)
            access_token = response.json()['access_token']
            authorization = 'Bearer ' + access_token
            params = {'fields': 'positions'}
            headers = {'Authorization': authorization}
            data = requests.get(TD_ACCOUNT_URL,params=params, headers=headers)
            data = data.json()
            return data
        except KeyError:
            print("Key Error")

    def formatTDAmeritradeData(self):
        data = self.getTDAmeritradeData()
        length = len(data['securitiesAccount']['positions'])
        symbols = [symbol['instrument']['symbol'] for symbol in data['securitiesAccount']['positions']]
        dayProfLoss = [round(data['securitiesAccount']['positions'][i]['currentDayProfitLoss'],2) for i in range(length)]
        dayProfLossPctg = [round(data['securitiesAccount']['positions'][i]['currentDayProfitLossPercentage'],2) for i in range(length)]
        shares = [round(data['securitiesAccount']['positions'][i]['longQuantity']) for i in range(length)]
        market_value = [round(data['securitiesAccount']['positions'][i]['marketValue'],3) for i in range(length)]
        purchase_price = [round(int(data['securitiesAccount']['positions'][i]['averagePrice']),3)*shares[i] for i in range(length)]
        totalProfLoss = [round(b-a,3) for a,b in zip(purchase_price, market_value)]
        categories = ['Day Profit/Loss','Day Profit/Loss PCTG', 'Total Profit/Loss','Shares','Market Value',
                    'Purchase Price']
        symbols.sort()
        if symbols[0] == '912810RP5':
            symbols[0] = 'T-Bond'
        info = zip(dayProfLoss,dayProfLossPctg,totalProfLoss,shares,market_value,purchase_price)
        values = [i for i in zip(symbols,[list(zip(categories,i)) for i in info])]
        info = {k:v for k,v in values}
        return info

    def getSimpleBankData(self):
        client = Client(client_id=SIMPLE_CLIENT_ID, secret=SIMPLE_SECRET, public_key=SIMPLE_PUBLIC_KEY, environment='development')
        warnings.filterwarnings("ignore")
        response = client.Accounts.balance.get(SIMPLE_ACCESS_TOKEN)
        accounts = response['accounts']
        accountSummary = {'Savings String': 'Savings Goal','Savings Balance':accounts[0]['balances']['current'],
        'StS String': 'Safe to Spend', 'StS Balance':accounts[1]['balances']['current']}
        return accountSummary

    def getMarcusCDData(self):
        start_date = dt.date(2020,5,26)
        cd_rate = .0135
        principal = 15_000
        daily_pay = round(principal*cd_rate/365,2)
        current_date = dt.datetime.now().date()
        money_made = int((current_date-start_date).days)*.55
        current_balance_marcus = principal + money_made
        Marcus_CD = {'Rate':cd_rate,'Principal':principal,'Money Made':money_made,'Current Balance':current_balance_marcus,
                    'Maturity Date': "May 26, 2021"}
        return Marcus_CD

    def getAllBalances(self):
        TD_Account_value = int(self.getTDAmeritradeData()['securitiesAccount']['currentBalances']['liquidationValue'])
        simple_bank_data = self.getSimpleBankData()
        simple_savings = int(simple_bank_data['Savings Balance'])
        simple_cash = int(simple_bank_data['StS Balance'])
        Simple_balance = simple_savings + simple_cash
        Marcus_balance = self.getMarcusCDData()['Current Balance']
        return {"TD Account Value":TD_Account_value, "Simple Account Value":{"Safe to Spend": simple_cash, "Savings": simple_savings}, "Marcus Account Value":
        Marcus_balance, "Total Balance": (TD_Account_value + Simple_balance + Marcus_balance)}


    def updateGoogleSheet(self):
        info = self.formatTDAmeritradeData()
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name('finances.json',scope)
        client = gspread.authorize(credentials)
        sheet = client.open('Finances').get_worksheet(3)
        sheet.update_cell(2,2,self.getAllBalances()['TD Account Value'])
        sheet.update_cell(3,2,self.getAllBalances()['Simple Account Value']['Safe to Spend'])
        sheet.update_cell(4,2,self.getAllBalances()['Simple Account Value']['Savings'])
        sheet.update_cell(5,2,self.getAllBalances()['Marcus Account Value'])
        estimated_balance = client.open('Finances').get_worksheet(6)
        estimated_balance.get_all_records()
        stocks = client.open('Finances').get_worksheet(4)
        keys = list(info.keys())[:-1]
        for i in range(len(keys)):
            for j in range(1,10):
                if j == 1:
                    stocks.update_cell(j,i+2,list(info.keys())[i])
                elif j != 1 and j < 8 :
                    number = j-2
                    stocks.update_cell(j,i+2,info[list(info.keys())[i]][number][1])
        self.estimated_balance = estimated_balance.get('D4')[0][0]
        print("Google Sheet Updated")

    def getDailyQuote(self):
        r = requests.get('https://type.fit/api/quotes')
        quotes = [i for i in range(len(r.json()[i]))]
        quote = choice(quotes)
        if quote['author'] != 'None':
            quote = f"""Quote of the Day:
        {quote['text']}
        -{quote['author']}"""
        else:
            quote = f"""Quote of the Day:
        {quote['text']}"""

    def getWeatherData(self):
        city = 'Houston'
        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=imperial'
        description = requests.get(url).json()['weather'][0]['description']
        weather_data = requests.get(url).json()['main']['temp']
        weather = f"""Weather:
        It is {weather_data} with {description}"""

    def getStringDate(self):
        day = str(dt.datetime.now())[8:10]
        month = str(dt.datetime.now())[5:7]
        year = str(dt.datetime.now())[:4]
        month = numberToMonth(month)
        response = requests.get(f'http://worldtimeapi.org/api/ip/{IP_ADDRESS}').json()
        time =  str(response['datetime'][11:16])
        timezone = str(response['abbreviation'])
        time_int = int(time.split(":")[0]) 
        am_or_pm = ""
        if time_int < 12:
            am_or_pm = "AM"
        else:
            am_or_pm = "PM"

        if time_int > 12:
            time_int = time_int - 12
            time = str(time_int) + time[2:]
        return f'{month} {day}, {year} at {time}{am_or_pm} {timezone}'

    def getEmailString(self):
        nline = '''
        '''
        tab = '  '
        msg = f"""Good Morning. Here is your update for {self.getStringDate()}:
{self.getDailyQuote()}
{self.getWeatherData()}
        """
        return msg

    def sendEmail(self):
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(EMAIL_ADDRESS,EMAIL_PASSWORD)
            subject = f'Update for {self.getStringDate()}'
            msg = f'Subject: {subject}\n\n{self.getEmailString()}'
            smtp.sendmail(EMAIL_ADDRESS,EMAIL_ADDRESS,msg)
        print("Email Sent")

if runProgram:
    dailyEmail = DailyEmail()
    dailyEmail.updateGoogleSheet()
    dailyEmail.sendEmail()
    print(f"Script Run on {dailyEmail.getStringDate()}")
else:
    print("The script did not execute. Incorrect Time.")
    print(f"Script Run on {dailyEmail.getStringDate()}")


















# total_balance = int(account_value) + int(current_balance_marcus) + int(simple_total_balance)
# total_balance = '$' + str(total_balance)[:2] + ',' + str(total_balance)[2:]
# account_value = str(account_value)[:2] + "," + str(account_value)[2:] 
# current_balance_marcus = str(current_balance_marcus)[:2] + ',' + str(current_balance_marcus)[2:]
# nline = '''
# '''
# tab = '  '
# body = f"""Good Morning. Here is your update for {date}:

# {quote}

# {weather}


# Finances:
# TD Ameritrade - ${account_value}
# Simple - ${simple_total_balance}
# Marcus - ${current_balance_marcus}
# Total Balance - {total_balance}
# Est. Grad Balance - {graduation_balance}
#     {nline}TD Ameritrade
#     {nline}{tab}{tab}{T['Symbol']}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(T['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(T['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(T['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(T['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(T['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(T['Purchase Price'],2)}
#     {nline}{tab}{tab}{VBK['Symbol'][0]}{VBK['Symbol'][1]}{VBK['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(VBK['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(VBK['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(VBK['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(VBK['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(VBK['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(VBK['Purchase Price'],2)}
#     {nline}{tab}{tab}{XLK['Symbol'][0]}{XLK['Symbol'][1]}{XLK['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(XLK['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(XLK['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(XLK['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(XLK['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(XLK['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(XLK['Purchase Price'],2)}
#     {nline}{tab}{tab}{NVDA['Symbol'][0]}{NVDA['Symbol'][1]}{NVDA['Symbol'][2]}{NVDA['Symbol'][3]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(NVDA['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(NVDA['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(NVDA['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(NVDA['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(NVDA['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(NVDA['Purchase Price'],2)}
#     {nline}{tab}{tab}{RIG['Symbol'][0]}{RIG['Symbol'][1]}{RIG['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(RIG['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(RIG['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(RIG['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(RIG['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(RIG['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(RIG['Purchase Price'],2)}
#     {nline}{tab}{tab}{PTON['Symbol'][0]}{PTON['Symbol'][1]}{PTON['Symbol'][2]}{PTON['Symbol'][3]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(PTON['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(PTON['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(PTON['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(PTON['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(PTON['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(PTON['Purchase Price'],2)}
#     {nline}{tab}{tab}{QQQ['Symbol'][0]}{QQQ['Symbol'][1]}{QQQ['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(QQQ['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(QQQ['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(QQQ['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(QQQ['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(QQQ['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(QQQ['Purchase Price'],2)}
#     {nline}{tab}{tab}{XLG['Symbol'][0]}{XLG['Symbol'][1]}{XLG['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(XLG['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(XLG['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(XLG['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(XLG['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(XLG['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(XLG['Purchase Price'],2)}
#     {nline}{tab}{tab}{ARKK['Symbol'][0]}{ARKK['Symbol'][1]}{ARKK['Symbol'][2]}{ARKK['Symbol'][3]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(ARKK['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(ARKK['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(ARKK['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(ARKK['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(ARKK['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(ARKK['Purchase Price'],2)}
#     {nline}{tab}{tab}{DIA['Symbol'][0]}{DIA['Symbol'][1]}{DIA['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(DIA['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(DIA['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(DIA['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(DIA['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(DIA['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(DIA['Purchase Price'],2)}
#     {nline}{tab}{tab}{VGT['Symbol'][0]}{VGT['Symbol'][1]}{VGT['Symbol'][2]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {round(VGT['currentDayProfitLoss'],2)}
#     {nline}{tab}{tab}{tab}Profit/Loss Percentage: {round(VGT['currentDayProfitLossPercentage'],2)}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(VGT['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(VGT['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(VGT['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(VGT['Purchase Price'],2)}
#     {nline}{tab}{tab}{T_BOND['Symbol'][0]}{T_BOND['Symbol'][1]}{T_BOND['Symbol'][2]}{T_BOND['Symbol'][3]}{T_BOND['Symbol'][4]}{T_BOND['Symbol'][5]}{T_BOND['Symbol'][6]}{T_BOND['Symbol'][7]}{T_BOND['Symbol'][8]}{T_BOND['Symbol'][9]}{T_BOND['Symbol'][10]}{T_BOND['Symbol'][11]}{T_BOND['Symbol'][12]}
#     {nline}{tab}{tab}{tab}Profit/Loss: {T_BOND['Maturity Date']}
#     {nline}{tab}{tab}{tab}Total Profit/Loss: {round(T_BOND['Total Profit/Loss'],2)}
#     {nline}{tab}{tab}{tab}Shares: {round(T_BOND['Shares'])}
#     {nline}{tab}{tab}{tab}Market Value: {round(T_BOND['marketValue'],2)}
#     {nline}{tab}{tab}{tab}Purchase Price: {round(T_BOND['Purchase Price'],2)}
    
#     {nline}{tab}Simple Bank
#     {nline}{tab}{tab}{tab}{SAFE_TO_SPEND['Category']}: {SAFE_TO_SPEND['Balance']}
#     {nline}{tab}{tab}{tab}{SAVINGS_GOALS['Category']}: {SAVINGS_GOALS['Balance']}
     
#     {nline}{tab}Marcus CD
#     {nline}{tab}{tab}{tab}{'Rate'}: {Marcus_CD['Rate']}
#     {nline}{tab}{tab}{tab}{'Principal'}: {Marcus_CD['Principal']}
#     {nline}{tab}{tab}{tab}{'Money Made'}: {round(Marcus_CD['Money Made'],2)}
#     {nline}{tab}{tab}{tab}{'Current Balance'}: {round(Marcus_CD['Current Balance'],2)}
#     {nline}{tab}{tab}{tab}{'Maturity Date'}: {Marcus_CD['Maturity Date']}
    
    
    
# Have a Nice Day
#     """
