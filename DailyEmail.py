# Plaid API (Simple Bank)
from plaid import Client
# Updating Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# Sending Email
import smtplib
# Other imports
import requests
import datetime as dt
import os
from random import choice
from dotenv import load_dotenv

load_dotenv()

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

# IP Address and City
IP_ADDRESS = os.environ.get('IP_ADDRESS')
CITY = os.environ.get('CITY')


# Printing String Months
def numberToMonth(number):
    number = int(number)
    if number == 1:
        return "January"
    if number == 2:
        return "February"
    if number == 3:
        return "March"
    if number == 4:
        return "April"
    if number == 5:
        return 'May'
    if number == 6:
        return 'June'
    if number == 7:
        return "July"
    if number == 8:
        return "August"
    if number == 9:
        return 'September'
    if number == 10:
        return 'October'
    if number == 11:
        return 'November'
    if number == 12:
        return 'December'

# Print String Day of the Week
def getDayOfWeek(number):
    if number == 1:
        return "Monday"
    if number == 2:
        return "Tuesday"
    if number == 3:
        return "Wednesday"
    if number == 4:
        return "Thursday"
    if number == 5:
        return "Friday"
    if number == 6:
        return "Saturday"
    if number == 0:
        return "Sunday"

# Local Time Information
time = requests.get(f'http://worldtimeapi.org/api/ip/{IP_ADDRESS}').json()
time_info = str(time['datetime'])
year = time_info[:4]
month = time_info[5:7]
string_month = numberToMonth(month)
day = time_info[8:10]
hour = time_info[11:13]
minute = time_info[14:16]
day_of_week = getDayOfWeek(time['day_of_week'])
timezone = time['timezone']

# Checking if the script should be run
# will execute on weekdays onlu
weekno = int(time['day_of_week'])
runProgram = False

# Checks if it is a weekday
if weekno > 0 and weekno < 6:
    runProgram = True

# Displaying the date information without the time
def getStringDateNoTime():
    return " ".join(str(word) for word in getStringDateTime().split(" ")[:-1])

# Displaying the date information with the time
def getStringDateTime():
    if int(hour) <= 12:
        return f'{day_of_week} {string_month} {day}, {year} at {hour}:{minute}AM {timezone}'
    else:
        return f'{day_of_week} {string_month} {day}, {year} at {str(int(hour)-12)}:{minute}PM {timezone}'



# Accesses the following API's: TD Ameritrade, Simple Bank, OpenWeatherMap, Quote of the day, and Google Sheets
# The information is used to update a google sheet and an email is sent with account information if it is the proper time
class DailyEmail:
    def __init__(self):
        pass

    # Returns the json data from the TD Ameritrade API
    def getTDAmeritradeData(self):
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

    # Returns a dictionary with all of the position information and account balances from the API Call
    def formatTDAmeritradeData(self):
        data = self.getTDAmeritradeData()
        self.current_account_value = data['securitiesAccount']['currentBalances']['liquidationValue']
        length = len(data['securitiesAccount']['positions'])
        symbols = [symbol['instrument']['symbol'] for symbol in data['securitiesAccount']['positions']]
        dayProfLoss = [round(data['securitiesAccount']['positions'][i]['currentDayProfitLoss'],2) for i in range(length)]
        dayProfLossPctg = [round(data['securitiesAccount']['positions'][i]['currentDayProfitLossPercentage'],2)/100 for i in range(length)]
        shares = [round(data['securitiesAccount']['positions'][i]['longQuantity']) for i in range(length)]
        market_value = [round(data['securitiesAccount']['positions'][i]['marketValue'],2) for i in range(length)]
        purchase_price = [round(int(data['securitiesAccount']['positions'][i]['averagePrice']),2)*shares[i] for i in range(length)]
        totalProfLoss = [round(b-a,3) for a,b in zip(purchase_price, market_value)]
        categories = ['Day Profit/Loss','Day Profit/Loss PCTG', 'Total Profit/Loss','Shares','Market Value',
                        'Purchase Price']
        for i in range(len(symbols)):
            if symbols[i] == '912810RP5':
                symbols[i] = 'T-Bond'
        info = zip(dayProfLoss,dayProfLossPctg,totalProfLoss,shares,market_value,purchase_price)
        values = [i for i in zip(symbols,[list(zip(categories,i)) for i in info])]
        info = {k:v for k,v in values}
        info.update({'Account Value': self.current_account_value})
        return info

    # Returns a dictionary with all the data returned from the plaid api for simple bank    
    def getSimpleBankData(self):
        client = Client(client_id=SIMPLE_CLIENT_ID, secret=SIMPLE_SECRET, public_key=SIMPLE_PUBLIC_KEY, environment='development')
        response = client.Accounts.balance.get(SIMPLE_ACCESS_TOKEN)
        accounts = response['accounts']
        accountSummary = {'Savings String': 'Savings Goal','Savings Balance':accounts[0]['balances']['current'],
        'StS String': 'Safe to Spend', 'StS Balance':accounts[1]['balances']['current']}
        return accountSummary

    # Returns a dictionary for all of the relevant CD information from Marcus
    def getMarcusCDData(self):
        start_date = dt.date(2020,5,26)
        cd_rate = .0135
        principal = 15_000
        current_date = dt.date(int(year),int(month),int(day))
        daily_pay = round(principal*cd_rate/365,2)
        money_made = int((current_date-start_date).days)*daily_pay
        current_balance_marcus = principal + money_made
        Marcus_CD = {'Rate':cd_rate,'Principal':principal,'Money Made':money_made,'Current Balance':current_balance_marcus,
                    'Maturity Date': "May 26, 2021"}
        return Marcus_CD

    # Returns a dictionary with all balances across the three accounts
    def getAllBalances(self):
        TD_Account_value = int(self.getTDAmeritradeData()['securitiesAccount']['currentBalances']['liquidationValue'])
        simple_bank_data = self.getSimpleBankData()
        simple_savings = int(simple_bank_data['Savings Balance'])
        simple_cash = int(simple_bank_data['StS Balance'])
        Simple_balance = simple_savings + simple_cash
        Marcus_data = self.getMarcusCDData()
        Marcus_rate = Marcus_data['Rate']
        Marcus_Principal = Marcus_data['Principal']
        Marcus_Money_Made = Marcus_data['Money Made']
        Marcus_maturity_date = Marcus_data['Maturity Date']
        Marcus_balance = Marcus_data['Current Balance']
        return {"TD Account Value":TD_Account_value, "Simple Account Value":{"Total": simple_cash + simple_savings,"Safe to Spend": simple_cash, "Savings": simple_savings}, "Marcus Account":
        {"Rate":Marcus_rate,"Principal":Marcus_Principal,"Money Made":Marcus_Money_Made,"Current Balance":Marcus_balance,"Maturity Date":Marcus_maturity_date}, "Total Balance": (TD_Account_value + Simple_balance + Marcus_balance)}

    # Updates all relevant cells with the account data using the google sheets api
    def updateGoogleSheet(self):
        info = self.formatTDAmeritradeData()
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name('/home/jlev111/Finances/finances.json',scope)
        client = gspread.authorize(credentials)
        sheet = client.open('Finances').get_worksheet(3)
        sheet.update_cell(2,2,self.getAllBalances()['TD Account Value'])
        sheet.update_cell(3,2,self.getAllBalances()['Simple Account Value']['Safe to Spend'])
        sheet.update_cell(4,2,self.getAllBalances()['Simple Account Value']['Savings'])
        sheet.update_cell(5,2,self.getAllBalances()['Marcus Account']['Current Balance'])
        sheet.update_cell(9,1,getStringDateTime())
        estimated_balance = client.open('Finances').get_worksheet(6)
        self.estimated_balance = estimated_balance.get('D4')[0][0]
        self.stocks = client.open('Finances').get_worksheet(4)
        self.stocks.update_cell(10,1,getStringDateTime())
        keys = list(info.keys())[:-1]
        for i in range(len(keys)):
            for j in range(1,10):
                if j == 1:
                    self.stocks.update_cell(j,i+2,list(info.keys())[i])
                elif j != 1 and j < 8 :
                    number = j-2
                    self.stocks.update_cell(j,i+2,info[list(info.keys())[i]][number][1])
        print("Google Sheet Updated")

    # Returns a random dauly quote and the author from a quote api
    def getDailyQuote(self):
        r = requests.get('https://type.fit/api/quotes')
        quotes = [quote for quote in r.json()]
        quote = choice(quotes)
        if quote['author'] != 'None':
            return f"""Quote of the Day:
{quote['text']}
-{quote['author']}"""
        else:
            return f"""Quote of the Day:
{quote['text']}"""

    # Returns local weather data using the OpenWeatherMap API
    def getWeatherData(self):
        url = f'http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_KEY}&units=imperial'
        description = requests.get(url).json()['weather'][0]['description']
        weather_data = requests.get(url).json()['main']['temp']
        return f"""Weather:
It is {weather_data} with {description}"""

    # Returns a string containing all of the positions 
    def getPositionsString(self):
        info = self.formatTDAmeritradeData()
        string = ""
        for k,v in info.items():
            if k != "Account Value":
                string += k
                string += '\n'
                string += "Day Profit/Loss: " + str(round(v[0][1],2))
                string += '\n'
                string += "Day Profit/Loss PCTG: " + str(round(v[1][1],2))
                string += '\n'
                string += "Total Profit/Loss: " + str(round(v[2][1],2))
                string += '\n'
                string += "Shares: " + str(round(v[3][1],2))
                string += '\n'
                string += "Market Value: " + str(round(v[4][1],2))
                string += '\n'
                string += "Purchase Price: " + str(round(v[5][1],2))
                string += '\n\n'
        string = string[:-2]
        return string

    # Returns the body of the email string
    def getEmailString(self):
        balances = self.getAllBalances()
        return f"""Good Morning. Here is your update for {getStringDateNoTime()}:

{self.getDailyQuote()}

{self.getWeatherData()}

Finances:
TD Ameritrade - ${balances['TD Account Value']}
Simple - ${balances['Simple Account Value']['Total']}
Marcus - ${balances['Marcus Account']["Current Balance"]}
Total Balance - ${balances['Total Balance']}
Est. Grad Balance - {self.estimated_balance}

TD Ameritrade
Day Proft/Loss: {str(self.stocks.get('O2')[0][0])}
Day Proft/Loss PCTG: {str(self.stocks.get('O3')[0][0])}
Total Profit/Loss: {str(self.stocks.get('O4')[0][0])}

{self.getPositionsString()}

Simple Bank
Safe to Spend: {balances['Simple Account Value']['Safe to Spend']}
Savings Goal: {balances['Simple Account Value']['Savings']}
Balance: {balances['Simple Account Value']['Total']}

Marcus CD
Rate: {balances['Marcus Account']['Rate']}
Principal: {balances['Marcus Account']['Principal']}
Money Made: {round(balances['Marcus Account']['Money Made'],2)}
Current Balance: {round(balances['Marcus Account']['Current Balance'],2)}
Maturity Date: {balances['Marcus Account']['Maturity Date']}

Have a Nice Day :)
        """

    # Sends an email with the desired string
    def sendEmail(self):
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(EMAIL_ADDRESS,EMAIL_PASSWORD)
            subject = f'Update for {getStringDateNoTime()}'
            msg = f'Subject: {subject}\n\n{self.getEmailString()}'
            smtp.sendmail(EMAIL_ADDRESS,EMAIL_ADDRESS,msg)
        print("Email Sent")

# If it is a weekday, the program will run
if runProgram:
    dailyEmail = DailyEmail()
    dailyEmail.updateGoogleSheet()
    dailyEmail.sendEmail()
    print(f"Dated - {getStringDateTime()}")
# Otherwise the script will display the time it was run
else:
    dailyEmail = DailyEmail()
    print("Script Not Run. Incorrect Time.")
    print(f"Dated - {getStringDateTime()}")
