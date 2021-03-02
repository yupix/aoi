import asyncio
import _thread as thread
import json
import os
import time

import MeCab
from dotenv import load_dotenv
from websocket import create_connection, WebSocketApp, WebSocketConnectionClosedException

with open("./templates/actions.json", encoding='utf-8') as action_list_file:
	action_list = json.load(action_list_file)

load_dotenv()
url = os.environ.get('websocket_url')


class Api:
	def __init__(self):
		pass

	def send(self, endpoint=None, data=None):
		content = ({
			"type": "api",
			"body": {
				"endpoint": f"{endpoint}",
				"data": {}
			}
		})
		for key, value in data.items():
			content['body']['data'][key] = value
		print(content)
		api_ws = create_connection(f'{url}')
		api_ws.send(json.dumps(content))
		result = api_ws.recv()
		print(result)


class Analysis:
	def __init__(self, text=None, original_node=None, message=None):
		self.text = text
		self.node = None
		self.remaining = None
		self.message = message

	def run(self):
		print('run')
		m = MeCab.Tagger("-Owakati")
		str_output = m.parse(self.text)
		node = str_output.split(' ')

		self.node = node
		return self.check_action()

	def check_action(self):
		"""形態素解析の結果からトリガーを起動する"""
		hit = False
		hit_word = ''
		remaining = ''
		for i in self.node:
			if i is True:
				remaining += i
			if i in action_list:
				hit = True
				hit_word = i

		if hit is True:
			aoi_instance = AoiAction(remaining=remaining)
			getattr(aoi_instance, action_list[f'{hit_word}'])(self.message)


class AoiAction(Analysis):
	def __init__(self, remaining=None):
		super().__init__(remaining)

	def follow(self, message=None):
		"""フォローに関する処理"""
		print('こちらがフォローです')
		print(message)
		api = Api()
		data = {'userId': message['body']['body']['userId']}
		api.send('following/create', data)
		print('終わった')
		print(message['body']['body']['note']['id'])
		data = {'noteId': f'{message["body"]["body"]["note"]["id"]}', 'reaction': 'love', 'dislike': 'true'}
		api.send('notes/reactions/create', data)


def on_message(ws, message):
	message = json.loads(message)
	print(message)
	if str(message['body']['type']) == 'mention':
		analysis = Analysis(text=message['body']['body']['text'], message=message)
		analysis.run()


def on_error(ws, error):
	print(error)


def on_close(ws):
	print("### closed ###")


def on_open(ws):
	def run(*args):
		try:
			ws.send(json.dumps({
				"type": "connect",
				"body": {
					"channel": "main",
					"id": "main"
				}

			}))
		except WebSocketConnectionClosedException:
			print('切断されました')

	# ws.close()

	thread.start_new_thread(run, ())


if __name__ == "__main__":
	ws = WebSocketApp(f'{url}', on_open=on_open,
					  on_message=on_message,
					  on_error=on_error,
					  on_close=on_close)
	ws.run_forever()
