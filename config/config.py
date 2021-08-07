import os
import configparser


class Config:
    def __init__(self):
        self.repeat_timer = os.environ.get('REPEAT_TIMER')
        self.conf_file_path = os.environ.get('CONF_FILE')
        self.conf_file_contents = self.read_config()

    def getTimer(self):
        return os.environ.get('REPEAT_TIMER')

    def read_config(self):
        # open config file
        try:
            config = configparser.ConfigParser()
            config.read(self.conf_file_path)
            config.sections()
            return config
        except IOError:
            log.critical("*********** ERROR reading config file **********")
            exit(1)
