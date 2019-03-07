import time
import sys

import json
import requests

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.gen
import logging


from tornado.options import define, options

import tornado.queues




define("port", default=8888, help="run on the given port", type=int)

q = tornado.queues.Queue(maxsize=4)

class NoResultError(Exception):
    pass



class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/result/(\d+)", RESULT),
            (r"/send", SEND),
        ]

        super(Application, self).__init__(handlers)


class Quotes():
    def __init__(self):

        self.tasks = {}
        self.id_counter = 1
        self.worked_task = []
        self.need_work_task = []
        tornado.ioloop.IOLoop.current().spawn_callback(worker)




    async def new_task(self,URL):
        if URL not in list([url_["url"] for url_ in self.tasks.values()]):
            self.tasks[str(self.id_counter)] = \
                {
                "url":URL,
                "Status":"New",
                "RESP C Len": 0,
                "RESP Status": "None",
                "RESP Body" : "None"
                    }

            logger.info("save new task {0}".format(self.tasks[str(self.id_counter)]))

            await q.put(self.id_counter)
            # await q.join()
            self.need_work_task.append(self.id_counter)

            self.id_counter += 1

            return


    def info(self,num_q):
        logger.info("Info of task {0} {1}".format(num_q,self.tasks[str(num_q)]))
        if str(num_q) in self.tasks.keys():
            return self.tasks[str(num_q)]
        else:
            logger.info("Info of task {0} id not founded".format(num_q))
            return {"info":"id not founded"}

    async def get_url(self,count_id):

        try:
            logger.info("Get page ingormation")
            self.tasks[str(count_id)]["Status"] = "Pending"
            logger.info("Task id: {0} status is Pending".format(count_id))
            res = requests.get(self.tasks[str(count_id)]["url"])
            self.tasks[str(count_id)]["RESP Status"] = res.status_code
            self.tasks[str(count_id)]["RESP Body"] = res.text
            self.tasks[str(count_id)]["RESP C Len"] = len(res.text)

            self.tasks[str(count_id)]["Status"] = "Completed"
            logger.info("Task id: {0} status is Completed".format(count_id))
        except:
            logger.info("Task id: {0} status is Error".format(count_id))
            self.tasks[str(count_id)]["Status"] = "Error"



async def worker():

    async for count_id in q:
        if count_id is None:
            return

        try:
            await Q.get_url(count_id)
        except:
            logger.info("Worker error get_url")
        finally:
            q.task_done()
            q.join()


class RESULT(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        logger.info("Get info of task id: {0}".format(args[0]))
        resp = {}
        resp["id"] = args[0]

        if args[0] in list(Q.tasks.keys()):
            resp.update(Q.info(args[0]))
            resp["Error"] = "None"
        else:
            resp["Error"] = "Task ID not defined"
        return self.write(json.dumps(resp))

class SEND(tornado.web.RequestHandler):
    async def post(self, *args, **kwargs):


        data = json.loads(self.request.body.decode().rstrip())

        logger.info("post {0}".format(data))
        await Q.new_task(data['url'])
        resp = data


        id_ = Q.id_counter-1
        if id_:

            logger.info("Creat new task id: {1} url: {0}".format(data['url'],id_))

            resp["task id"] = str(id_)
            resp["Error"] = "None"

        else:
            logger.info("Url: {0} waiting of Quotes".format(data['url']))
            resp["Error"] = "Url in Quotes"

        try:
            self.write(json.dumps(resp))


        except Exception as e:
            resp["Error"] = ""

            self.write(json.dumps(resp))
            logger.warning(e)

        finally:
            self.finish()


def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler('log.txt', mode='a')
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger



async def main():



        app = Application()
        app.listen(options.port)
        logger.info("Run server")
        shutdown_event = tornado.locks.Event()
        await shutdown_event.wait()


if __name__ == "__main__":

    Q = Quotes()
    logger = setup_custom_logger('Quotes')
    logger.info("Start app")
    tornado.ioloop.IOLoop.current().run_sync(main)