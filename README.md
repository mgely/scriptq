ScriptQ
====================================================

An easy way to run your python scripts one after the other. 
You can add more scripts to the queue, as well as edit the content and order of added scripts as you go.

Installation
------------

Open a terminal and run ``pip install scriptq``.

To launch the program run ``python -m scriptq``.


Documentation
-------------

![image](documentation.PNG)

Optional: setting up email notifications
----------------------------------------

ScriptQ can optionally send an email to one or multiple addresses when a script ends.
This email will contain the script path, the status with which the script ended (success or failure), and the output that the script would print in a command prompt.

**How to set this up?**

 - [Create a gmail address](https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp
) from which ScriptQ will send the emails
 - Allow "less secure" apps to access that gmail account. Log in to your newly created gmail account, head to [this link](https://myaccount.google.com/lesssecureapps), and switch "Allow less secure apps" to ON. **Warning**: be very careful to not do this on your personal gmail account, I would recommend using an "incognito" window for this step.
 - Edit the ScriptQ settings file located at `python_directory\Lib\site-packages\scriptq\settings.py` as follows

```
gmail_notifications = {
    'enable' : True,
    'sender_email': "my_newly_created_address@gmail.com",
    'sender_password': "my_newly_created_password",
    'receiver_emails': ["alice@bla.com","bob@blob.net"]
}
```



Developper information
----------------------

[![Downloads](https://pepy.tech/badge/scriptq)](https://pepy.tech/project/scriptq)
[![Build Status](https://travis-ci.com/mgely/scriptq.svg?branch=master)](https://travis-ci.com/mgely/scriptq)
[![codecov](https://codecov.io/gh/mgely/scriptq/branch/master/graph/badge.svg)](https://codecov.io/gh/mgely/scriptq)

