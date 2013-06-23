# -*- coding: utf-8 -*-

import os
import sys
import threading
import time
import ConfigParser

import clicore
from dropbox import client, session, rest

import utils


def login_required():
    """decorator for handling authentication and exceptions"""
    def decorate(f):
        def wrapper(self, item, args, line):
            if not self._session.is_linked():
                print "Please login to execute this command"
                return
            try:
                return f(self, item, args, line)
            except rest.ErrorResponse, e:
                print "Error: %s" % e
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorate


class DropboxCLI(clicore.Cli):
    def __init__(self):
        clicore.Cli.__init__(self, ".dbc.history")
        self._config_file = os.path.join(os.environ["HOME"], ".dbc")

        if self._is_first_execution():
            self._ask_for_dropbox_settings()

        self._read_config_file()

        self._session = StoredSession(self._config.get("app_key"), self._config.get("app_secret"), self._config.get("access_type", "app_folder"))
        self._api_client = client.DropboxClient(self._session)
        self._current_path = ""
        self.set_prompt("Dropbox> ")
        self._session.load_creds()

        self._watchdog = Watchdog(self)
        self._watchdog.start()

        # register default items
        self.register_item(clicore.CliItem("login", self.cmd_login, categories=["logged_out"]))

        # items when session is established
        self.register_item(clicore.CliItem("logout", self.cmd_logout, categories=["logged_in"]))
        self.register_item(clicore.CliItem("info", self.cmd_info, categories=["logged_in"]))
        self.register_item(clicore.CliItem("ls", self.cmd_ls, categories=["logged_in"]))
        self.register_item(clicore.CliItem("mkdir", self.cmd_mkdir, categories=["logged_in"]))
        self.register_item(clicore.CliItem("rm", self.cmd_rm, categories=["logged_in"]))
        self.register_item(clicore.CliItem("mv", self.cmd_mv, categories=["logged_in"]))
        self.register_item(clicore.CliItem("get", self.cmd_get, categories=["logged_in"]))
        self.register_item(clicore.CliItem("put", self.cmd_put, subitems=[clicore.CliSysPathItem()], categories=["logged_in"]))

    def stop(self):
        clicore.Cli.stop(self)
        self._watchdog.stop()

    def _read_config_file(self):
        parser = ConfigParser.SafeConfigParser()
        parser.read(self._config_file)
        self._config = {}
        try:
            self._config["app_key"] = parser.get("dropbox_settings", "app_key")
            self._config["app_secret"] = parser.get("dropbox_settings", "app_secret")
            self._config["access_type"] = parser.get("dropbox_settings", "access_type")
        except:
            pass

    def _is_first_execution(self):
        return not os.path.exists(self._config_file)

    def _ask_for_dropbox_settings(self):
        print("This is your first execution of the dropbox-cli or no configuration file was found.")
        print("If you want to use this dropbox-cli you have to create a new app for you in your dropbox account.")
        print("Thus, go to 'https://www.dropbox.com/developers/apps' and click 'create an app'.")
        print("There you have to enter the following:")
        print("App name: db-cli")
        print("Description: here you can enter whatever you want")
        print("Access: choose the type you want to use")
        print("Then click 'create' and press enter in this cli to continue")
        raw_input()
        print("In your created app option page you find the app key and your app secret key")
        print("Please enter them:")
        app_key = raw_input("App key: ")
        app_secret = raw_input("App secret: ")
        access_type = raw_input("Press 1 for the access type 'App folder' and 2 for 'Full Dropbox': ")
        access_types = ["app_folder", "dropbox"]
        try:
            access_type = access_types[int(access_type) - 1]
        except (KeyError, ValueError):
            print("This was not 1 or 2 - try again")
            sys.exit(1)

        parser = ConfigParser.SafeConfigParser()
        parser.add_section("dropbox_settings")
        parser.set("dropbox_settings", "app_key", app_key)
        parser.set("dropbox_settings", "app_secret", app_secret)
        parser.set("dropbox_settings", "access_type", access_type)
        parser.write(open(self._config_file, "w+"))

    def watch(self):
        """method for watchdog"""
        self.enable_items_by_category("logged_in" if self._session.is_linked() else "logged_out")

    def cmd_login(self, item, args, line):
        """login to a dropbox account"""
        try:
            self._session.link()
        except rest.ErrorResponse, e:
            print "Error: %s" % e

    @login_required()
    def cmd_logout(self, item, args, line):
        """logout of the current dropbox account session"""
        self._session.unlink()
        self._current_path = ''
        print "You are not logged in anymore"

    @login_required()
    def cmd_ls(self, item, args, line):
        """list files in current remote dropbox directory"""
        response = self._api_client.metadata(self._current_path)

        if "contents" in response:
            contents = sorted(response["contents"], key=lambda k: not k["is_dir"])
            ls = []
            for f in contents:
                ls.append(["DIR" if f["is_dir"] else "FILE", f["size"], f["modified"], os.path.basename(f["path"]) + ("/" if f["is_dir"] else "")])
            utils.print_readable_table(ls)
        else:
            print "directory is empty"

    @login_required()
    def cmd_mkdir(self, item, args, line):
        """create a new directory in the current path"""
        self._api_client.file_create_folder(self._current_path + "/" + args)

    @login_required()
    def cmd_rm(self, item, args, line):
        """delete a file or a directory"""
        self._api_client.file_delete(os.path.join(self._current_path, args))

    @login_required()
    def cmd_mv(self, item, args, line):
        """move/rename a file or directory"""
        paths = args.split()
        if len(paths) < 2:
            print "minimum two arguments are requried 'mv <source> <dest>'"
            return False
        target = os.path.join(self._current_path, paths[-1])
        if len(paths) == 2:
            metadata_of_target = self._api_client.metadata(target)

            if metadata_of_target["is_dir"]:
                if paths[1] == ".":
                    t = os.path.join(self._current_path, os.path.basename(paths[0]))
                else:
                    t = os.path.join(self._current_path, paths[1], paths[0])
                self._api_client.file_move(os.path.join(self._current_path, paths[0]), t)
                return True

            self._api_client.file_move(os.path.join(self._current_path, paths[0]), os.path.join(self._current_path, paths[1]))
            return True

        try:
            metadata_of_target = self._api_client.metadata(target)
        except rest.ErrorResponse, e:
            if e.status == 404:
                print "target '%s' does not exist" % target
                return False
        if not metadata_of_target["is_dir"]:
            print "target '%s' is not a directory" % target
            return False

        for p in paths[:-1]:
            s = os.path.join(self._current_path, p)
            t = os.path.join(self._current_path, os.path.basename(p)) if target == "." else os.path.join(target, p)
            print "move file '%s' to '%s'" % (s, t)
            self._api_client.file_move(s, t)

    @login_required()
    def cmd_get(self, item, args, line):
        paths = args.split()
        if len(paths) < 2:
            print "minimum two arguments are requried 'mv <source> <dest>'"
            return False
        target_file, metadata = self._api_client.get_file_and_metadata(os.path.join(self._current_path, paths[0]))
        target_filename = os.path.basename(paths[0]) if paths[1] == "." else paths[1]
        with open(os.path.expanduser(target_filename), "wb") as f:
            f.write(target_file.read())
        print "wrote %s from remote '%s' to local '%s'" % (metadata["size"], paths[0], target_filename)

    @login_required()
    def cmd_put(self, item, args, line):
        paths = args.split()
        if len(paths) < 2:
            print "minimum two arguments are requried 'mv <source> <dest>'"
            return False
        if not os.path.exists(paths[0]):
            print "local file '%s' does not exist" % paths[0]
            return False
        if paths[1] == ".":
            paths[1] = os.path.basename(paths[0])
        with open(os.path.expanduser(paths[0]), "rb") as f:
            self._api_client.put_file(os.path.join(self._current_path, paths[1]), f)

    @login_required()
    def cmd_info(self, item, args, line):
        """display dropbox account infos"""
        info = self._api_client.account_info()
        data = [
            ["Name: ", info["display_name"]],
            ["User Id: ", info["uid"]],
            ["Email: ", info["email"]],
            ["Country: ", info["country"]],
            ["Total space: ", utils.human_readable_size(info["quota_info"]["quota"])],
            ["Normal space: ", utils.human_readable_size(info["quota_info"]["normal"])],
            ["Shared space: ", utils.human_readable_size(info["quota_info"]["shared"])]
        ]
        utils.print_readable_table(data)


class StoredSession(session.DropboxSession):
    """a wrapper around DropboxSession that stores a token to a file on disk"""
    TOKEN_FILE = ".token_store.txt"

    def load_creds(self):
        try:
            stored_creds = open(self.TOKEN_FILE).read()
            self.set_token(*stored_creds.split("|"))
            print "[loaded access token]"
        except IOError:  # TOKEN_FILE could not be loaded
            pass

    def write_creds(self, token):
        with open(self.TOKEN_FILE, "w") as f:
            f.write("|".join([token.key, token.secret]))

    def delete_creds(self):
        os.unlink(self.TOKEN_FILE)

    def link(self):
        request_token = self.obtain_request_token()
        url = self.build_authorize_url(request_token)
        print "url: ", url
        print "Please authorize in the browser. After you're done, press enter."
        raw_input()

        self.obtain_access_token(request_token)
        self.write_creds(self.token)

    def unlink(self):
        self.delete_creds()
        session.DropboxSession.unlink(self)


class Watchdog(threading.Thread):
    def __init__(self, cli):
        threading.Thread.__init__(self)
        self._cli = cli

    def run(self):
        self._up = True
        while self._up:
            self._cli.watch()
            time.sleep(0.5)

    def stop(self):
        self._up = False
