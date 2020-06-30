# Send Text
from twilio.rest import Client
# Google spreadsheet
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# Other Imports
import os
from dotenv import load_dotenv
import requests

load_dotenv()

# All Environment Variables ...
# TD
TD_REFRESH_TOKEN = os.environ.get('TD_REFRESH_TOKEN')
TD_REFRESH_URL = "https://api.tdameritrade.com/v1/oauth2/token"
TD_CLIENT_ID = os.environ.get('TD_CLIENT_ID')
TD_ACCOUNT_NUMBER = os.environ.get("TD_ACCOUNT_NUMBER")
TD_ACCOUNT_URL = "https://api.tdameritrade.com/v1/accounts/" + TD_ACCOUNT_NUMBER

# twilio
ACCOUNT_SID = os.environ.get('ACCOUNT_SID')
AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
FROM_NUMBER = os.environ.get('FROM_NUMBER')
TO_NUMBER = os.environ.get('TO_NUMBER')

# IP Address
IP_ADDRESS = os.environ.get('IP_ADDRESS')

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


weekno = int(time['day_of_week'])
runProgram = False
# Checks if it is a weekday and between the hours of 8 and 4
if weekno > 0 and weekno < 6 and int(str(time['datetime'])[11:13]) >= 8 and int(str(time['datetime'])[11:13]) <= 16:
    runProgram = True

# Returns the string date with the current time
def getStringDate():
    if int(hour) <= 12:
        return f'{day_of_week} {string_month} {day}, {year} at {hour}:{minute}AM {timezone}'
    else:
        return f'{day_of_week} {string_month} {day}, {year} at {str(int(hour)-12)}:{minute}PM {timezone}'

# Accesses the following API's: TD Ameritrade, Google Sheets, and Twilio
# The information is used to update a google sheet and send a text if it is the proper time
class TextUpdate:
    def __init__(self):
        pass

    # Updates all relevant cells with the account data using the google sheets api   
    def updateGoogleSheet(self):
        info = self.formatTDData()
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name('/home/jlev111/Finances/finances.json',scope)
        client = gspread.authorize(credentials)
        sheet = client.open('Finances').get_worksheet(3)
        sheet.update_cell(2,2,info['Account Value'])
        sheet.update_cell(9,1,getStringDate())
        self.stocks = client.open('Finances').get_worksheet(4)
        self.stocks.update_cell(10,1,getStringDate())
        keys = list(info.keys())[:-1]
        for i in range(len(keys)):
            for j in range(1,10):
                if j == 1:
                    self.stocks.update_cell(j,i+2,list(info.keys())[i])
                elif j != 1 and j < 8 :
                    number = j-2
                    self.stocks.update_cell(j,i+2,info[list(info.keys())[i]][number][1])
        print("Google Sheet Updated")

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

    # Returns a string containing all of the positions 
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

    # Returns the body of the message string
    def formatMessage(self):
        account_value = str(self.current_account_value)
        account_value_string = "$" + account_value[:2] + "," + account_value[2:]
        movement = ""
        if self.difference >= 0:
            movement = "Positive Movement"
        else:
            movement = "Negative Movement"
        return f"""{movement}
TD Balance: {account_value_string}
Day Proft/Loss: {str(self.stocks.get('O2')[0][0])}
Day Proft/Loss PCTG: {str(self.stocks.get('O3')[0][0])}
Total Profit/Loss: {str(self.stocks.get('O4')[0][0])}
\nYour account has moved ${round(self.difference,2)} in the last hour.
\nHere are your positions:
{self.getPositionsString()}

Dated - {getStringDate()}

Have a nice day :)
        """
    # checks if the conditions are correct to send a message
    def sendMessage(self):
        # Checks if the account has moved more than 100 dollars in the last hour
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

    # Reads a txt file to check its value and find the difference in account movement
    # if it is more than 100 it returns true
    # the sheet is written to with the current account value as of that time
    def checkForNecessaryUpdate(self):
        with open('/home/jlev111/Finances/Send.txt','r') as f:
            checked_account_value = eval(f.readline())
            f.close()
        self.difference = self.current_account_value - checked_account_value
        print("Amount difference was: " + str(round(self.difference,2)))
        if abs(self.difference) >= 100:
            with open('/home/jlev111/Finances/Send.txt','w') as f:
                f.write(str(round(self.current_account_value,2)))
                print("Text file updated")
                f.close()
                return True
        else:
            with open('/home/jlev111/Finances/Send.txt','w') as f:
                f.write(str(round(self.current_account_value,2)))
                print("Text file updated")
                f.close()
                return False

# checks if the conditions are correct to run the program
if runProgram:
    textupdate = TextUpdate()
    textupdate.updateGoogleSheet()
    textupdate.sendMessage()
    print(f"Dated - {getStringDate()}")
# Otherwise the script will display the time it was run
else:
    textupdate = TextUpdate()
    print("The script did not execute. Incorrect Time.")
    print(f"Dated - {getStringDate()}")
 