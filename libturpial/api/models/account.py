# -*- coding: utf-8 -*-

#from libturpial.common import *
from libturpial.lib.config import AccountConfig
from libturpial.api.models.profile import Profile
from libturpial.lib.protocols.twitter import twitter
from libturpial.lib.protocols.identica import identica

from libturpial.common import get_username_from, get_protocol_from, \
        ProtocolType, LoginStatus, build_account_id
from libturpial.common.exceptions import EmptyOAuthCredentials, \
        EmptyBasicCredentials, ErrorLoadingAccount


class Account(object):
    """
    This class holds all related methods to an user account. It contains a
    protocol instance associated to the user and the profile model to store the
    user details. This is the class you must instanciate if you want to handle
    a user account.

    Account let you perform two main actions: create a new account or load an
    existing one. To create a new valid account based on OAuth authentication
    do the following:

    >>> account = Account.new_oauth('twitter', 'my_user', 'key', 'secret', 'verifier')

    And to create a new one for Basic authentication:

    >>> account = Account.new_basic('identica', 'my_user', 'my_password')

    Both commands will create a new entry in *~/.config/turpial/accounts/*
    with all the information about configuration. An existing account can be
    loaded later only with the account id. For example:

    >>> account = Account.load('my_user-twitter')

    Or

    >>> account = Account.load('my_user-identica')

    From this point you can use the method described here to handle the
    *account* object.
    """

    def __init__(self, protocol_id, username):
        self.id_ = build_account_id(username, protocol_id)

        self.username = username
        self.protocol_id = protocol_id
        self.logged_in = LoginStatus.NONE

        self.columns = []
        self.profile = None
        self.friends = None
        self.lists = None

        if protocol_id == ProtocolType.TWITTER:
            self.protocol = twitter.Main()
        elif protocol_id == ProtocolType.IDENTICA:
            self.protocol = identica.Main()

        self.config = AccountConfig(self.id_)


    @staticmethod
    def new_oauth(protocol_id, username, key, secret, verifier):
        """
        Return a new account object based on OAuth authentication. This will
        create a new entry in *~/.config/turpial/accounts/* with all the
        configuration stuff. It needs the *username*, the OAuth *key*, the OAuth
        *secret* and the *verifier* (also known as PIN) given by the service.

        If the account exists this method overwrite the previous credentials
        """
        account = Account(protocol_id, username)
        account.setup_user_credentials(account.id_, key, secret, verifier)
        account.config.save_oauth_credentials(key, secret, verifier)
        return account

    @staticmethod
    def new_basic(protocol_id, username, password):
        """
        Return a new account object based on Basic authentication. This will
        create a new entry in *~/.config/turpial/accounts/* with all the
        configuration stuff. It needs the *username* and the *password*.

        If the account exists this method overwrite the previous credentials
        """
        account = Account(protocol_id, username)
        account.setup_user_credentials(account.id_, username, password)
        account.config.save_basic_credentials(username, password)
        return account

    @staticmethod
    def load(account_id):
        """
        Return the Account object associated to *account_id* loaded from
        existing configuration. If the *account_id* does not correspond to a
        valid account returns a
        :class:`libturpial.common.exceptions.ErrorLoadingAccount` exception.
        If credentials in configuration file are empty it returns a 
        :class:`libturpial.common.exceptions.EmptyOAuthCredentials` or a
        :class:`libturpial.common.exceptions.EmptyBasicCredentials` exception.
        """
        if not AccountConfig.exists(account_id):
            raise ErrorLoadingAccount

        username = get_username_from(account_id)
        protocol_id = get_protocol_from(account_id)

        account = Account(protocol_id, username)
        try:
            key, secret, verifier = account.config.load_oauth_credentials()
            account.setup_user_credentials(account.id_, key, secret, verifier)
        except EmptyOAuthCredentials:
            try:
                username, password = account.config.load_basic_credentials()
                account.setup_user_credentials(account.id_, username, password)
            except EmptyBasicCredentials:
                raise ErrorLoadingAccount
        return account

    def authenticate(self):
        self.profile = self.protocol.verify_credentials()
        self.lists = self.protocol.get_lists(self.profile.username)

        self.columns = [ColumnType.TIMELINE, ColumnType.REPLIES,
                        ColumnType.DIRECTS, ColumnType.SENT,
                        ColumnType.FAVORITES] + self.lists
        return self.id_

    def get_friends(self):
        self.friends = self.protocol.get_friends()
        return self.friends

    def get_columns(self):
        return self.columns

    def get_list_id(self, list_name):
        for li in self.lists:
            if li.name == list_name:
                return li.id_
        return None

    def remove(self, delete_all):
        if delete_all:
            self.config.dismiss()

    def delete_cache(self):
        self.config.delete_cache()

    def get_cache_size(self):
        return self.config.calculate_cache_size()

    def __getattr__(self, name):
        try:
            return getattr(self.protocol, name)
        except:
            try:
                return getattr(self.profile, name)
            except:
                raise AttributeError
