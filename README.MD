imap-mail-watcher
====

# ***<u>まだ完成していない</u>***  
imapを監視して、mattermostにメールの内容をルールに則って投稿するツール

## Description
slackが使えなくて、メール地獄に嵌っている人のためツール  
投稿に返信したら、メールに返信できたらいいなー  

## Requirement
### packages
- PyYAML/4.1
- mattermostdriver/5.0.0
- requests/2.19.1
### environment
メールがimap  
exchangeも多分大体使えるけど、検証しておりません

## Usage
1. setting.ymlを設定する  
  ```
  app:
  common:
    mattermost:
      scheme: <http>
      url: <mattermost url>
      port: <80>
      basepath: </api/v4>
      timeout: <30>
  users: # You need at least one user
    - name: <unique name>
      mattermost:
        token: <mattermost token>
        team_id: <teamname>
      imap:
        host: <hostname>
        user: <username>
        password: <password>
  ```
2. `python ./main.py`  

## Install
git clone https://github.com/shiva768/imap-mail-watcher.git

## Licence

[MIT](https://github.com/shiva768/cybozu-gcal-sync/blob/master/LICENSE)

## Author

[shiva768](https://github.com/shiva768)
