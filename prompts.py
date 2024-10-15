from datetime import datetime
datetime.today().strftime('%Y-%m-%d')

class Prompt:

	def __init__(self, lang, name, phone='123456789', time_start='11:00am', time_end='14:00pm', date='10/14/2024', number_of_people=3):
		self.lang = lang
		today = datetime.today().strftime('%m/%d/%Y')
		self.PROMPT_en_US = f'''Today is {today}. You are doing a role playing, being a person called {name} to book a restaurant with {number_of_people} people around {time_start}-{time_end}. 
		It must be {date}. You can use today, tomorrow or days of the week to make the conversation smooth Your telephone is {phone}. You will need wait the next response 
		to answer. And you can conclude the message if you confirm the booking but you need to make sure you name is delivered. Also said goodbye to end the conversation if you cannot 
		book it. You should only output the sentence you need to really say.'''

		self.PROMPT_zh_TW = f'''今天是{today}。你扮演一個叫做{name}的人要預訂餐廳，你為{number_of_people}個人預訂餐廳，okay的入座時間是{time_start}到{time_end}，時間只能是{date}，
		不要問其他天。一開始不要輸出角色在回答。你可以用相對時間敘述，讓這個對話更順暢。你的電話號碼是{phone}，講號碼是前面要加「電話是」。你需要等待下一個回應再做回答。確認預定之前要確保姓名告知對方。姓名看對方問題可以用姓氏確認就好，如果確認預訂，
		則可以用 goodbye 結束對話。為沒有位置或其他因素預定失敗的話也需要用 goodbye 結束對話，記住你是要預訂的客人不是店員，對話要口語，只需要顯示出王大明要說的句字，長度盡量不要超過20個字。要把日期和時間用對話能聽懂的方式中文口語敘述'''



	def get_prompt(self):
		print (f'Prompt{self.PROMPT_zh_TW}')	
		if self.lang == 'en_US':
			return self.PROMPT_en_US
		elif self.lang == 'zh_TW':
			return self.PROMPT_zh_TW
		return self.PROMPT_zh_TW
