from twilio.rest import Client
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
import datetime as dt

runProgram = False
weekno = dt.datetime.today().weekday()
time_change_from_utc = 5
time = int(str(dt.datetime.now().time().strftime('%H'))[1]) + time_change_from_utc

if weekno < 5 and time > 8 and time <= 15:
    runProgram = True

load_dotenv()

TD_REFRESH_TOKEN = os.environ.get('TD_REFRESH_TOKEN')
TD_REFRESH_URL = "https://api.tdameritrade.com/v1/oauth2/token"
TD_CLIENT_ID = os.environ.get('TD_CLIENT_ID')
TD_ACCOUNT_URL = f"https://api.tdameritrade.com/v1/accounts/{os.environ.get('TD_ACCOUNT_NUMBER')}"
TD_KEY = os.environ.get('TD_KEY')

ACCOUNT_SID = os.environ.get('ACCOUNT_SID')
AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
FROM_NUMBER = os.environ.get('FROM_NUMBER')
TO_NUMBER = os.environ.get('TO_NUMBER')

IP_ADDRESS = os.environ.get('IP_ADDRESS')

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

class TextUpdate:
    def __init__(self):
        pass

    def updateGoogleSheet(self):
        info = self.formatTDData()
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name('finances.json',scope)
        client = gspread.authorize(credentials)
        sheet = client.open('Finances').get_worksheet(3)
        sheet.update_cell(2,2,info['Account Value'])
        stocks = client.open('Finances').get_worksheet(4)
        keys = list(info.keys())[:-1]
        for i in range(len(keys)):
            for j in range(1,10):
                if j == 1:
                    stocks.update_cell(j,i+2,list(info.keys())[i])
                elif j != 1 and j < 8 :
                    number = j-2
                    stocks.update_cell(j,i+2,info[list(info.keys())[i]][number][1])
        print("Google Sheet Updated")


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

    def formatTDData(self):
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

    def getPositionsString(self):
        info = self.formatTDData()
        string = ""
        for d,v in info.items():
            if d != "Account Value":
                string += d 
                string += '\n'
                string += "Day Profit/Loss: " + str(round(v[0][1],2))
                string += '\n'
                string += "Total Profit/Loss: " + str(round(v[2][1],2))
                string += '\n'
                string += "Market Value: " + str(round(v[4][1],2))
                string += '\n'
                string += "Purchase Price: " + str(round(v[5][1],2))
                string += '\n\n'
        string = string[:-2]
        return string

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

    def formatMessage(self):
        account_value = str(self.current_account_value)
        account_value_string = "$" + account_value[:2] + "," + account_value[2:]
        movement = ""
        if self.difference >= 0:
            movement = "Positive Movement"
        else:
            movement = "Negative Movement"
        message = f"""{movement}
Your TD Account Balance is: {account_value_string}
\nYour account has moved ${round(self.difference,2)} in the last hour.
\nHere are your positions:
{self.getPositionsString()}

Dated - {self.getStringDate()}

Have a nice day :)
        """
        return message

    def sendMessage(self):
        if self.checkForNecessaryUpdate():
            message = self.formatMessage()
            client = Client(ACCOUNT_SID, AUTH_TOKEN)
            message = client.messages \
            .create(
                body=message,
                from_=FROM_NUMBER,
                to=TO_NUMBER
            )
            print("Message Sent")
        else:
            print("Message not sent")


    def checkForNecessaryUpdate(self):
        with open('Send.txt','r') as f:
            checked_account_value = eval(f.readline())
            f.close()
        self.difference = checked_account_value - self.current_account_value
        if abs(self.difference) >= 100:
            with open('Send.txt','w') as f:
                f.write(str(self.current_account_value))
                f.close()
                return True
        else:
            with open('Send.txt','w') as f:
                f.write(str(self.current_account_value))
                f.close()
                return False

if runProgram:
    textupdate = TextUpdate()
    textupdate.updateGoogleSheet()
    textupdate.sendMessage()
    print(f"Script Run on {textupdate.getStringDate()}")
else:
    print("The script did not execute. Incorrect Time.")
    print(f"Script Run on {textupdate.getStringDate()}")