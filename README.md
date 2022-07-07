# OFDL
Media downloader with graphical user interface using PyQt5.

Downloads media files from *OF* (images, videos, highlights, stories)

The only requirements should be requests and PyQt5

Before logging in, press F12 (or inspect/inspect element and go to the network tab) to bring up the "developer tools" and then log in. You should see "init" as shown below. If not, type in the search "init" and or refresh the page. Once you've found it, click on it.

<img src="https://raw.githubusercontent.com/Hashirama/OFDL/master/init.png">

Scroll down to the section "request headers" and everything you will need should be in this section (cookie, useragent, x-bc):

<img src="https://raw.githubusercontent.com/Hashirama/OFDL/master/request.png">


 Copy these three values:
 <img src="https://raw.githubusercontent.com/Hashirama/OFDL/master/cookie.png">
 <img src="https://raw.githubusercontent.com/Hashirama/OFDL/master/user_agent.png">
 <img src="https://raw.githubusercontent.com/Hashirama/OFDL/master/x_bc.png">
 
 and put them into the textbox displayed after you click on the buttons pointed at in the below image:
 
 <img src="https://raw.githubusercontent.com/Hashirama/OFDL/master/options.png">
 
 After you've added all three values, and you click the "x" button on the Options window, it should then fetch a list of your subscriptions.

 
 
 # Requirements

Written using Python 3.9 so use 3.9 or anything above.

The only two requirements/dependencies should be requests and PyQt5.

There is a "requirements.txt" file that can be used to install the dependencies at the command line: 

<pre><code>pip3 install -r requirements.txt</code></pre>

or 

<pre><code>pip3 install requests</code></pre>
<pre><code>pip3 install pyqt5</code></pre>

The main script is OFDL.py and can be run on some systems by double clicking it (usually Windows) or by going into the directory using terminal or the command line and executing:

<pre><code>python3 OFDL.py</code></pre>
