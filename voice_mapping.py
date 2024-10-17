class VoiceConfig:
	def __init__(self, lang):
		self.lang = lang

	def get_open_ai_voice(self):
		return 'alloy'

	def get_twilio_voice(self):
		if self.lang == 'zh-TW':
			return 'Google.cmn-TW-Wavenet-B'
		else:
			return 	'en-US-Standard-H'

