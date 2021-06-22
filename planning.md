# Well, lets see how this goes, shall we?

## Ideas:
* SQL database for individual files. Use that to store data like name, description and stuff like that. Also store file location. That, or just pull the name from it and match to the files directory
* Use PIL to turn PDF files into images for thumbnails. If the file is an image, just use that as a thumbnail. If any other type, get a stylized version of it's file thumbnail (Adobe Illustrator go brrrt) as the site thumbnail. If I can, turn .docx files into an image as well.
* For people's accounts, add a way to do custom names. That way NB people can change theirs. Make it default to their google one but you can change it.
* Searching is gunna be a pain. The best I can do is run fuzzy search against each criteria. The higher on the list each item is, the more "search points" it gets. Run this on all the criteria, then display items based on its search points.<br>
<strike>Or, compile all the criteria into a string (example: `"name-shortdesc-longdesc-subject-tags"`) and fuzzy search that. Not sure about the sensitivity of fuzzy search tho. If it's too low, it won't pick up the stuff.</strike><br>
Ok that doesn't work. Just gunna do the other idea.
* <strong> FOR THE LOVE OF GOD ENCODE ALL FILE NAMES TO BASE 64</strong><br>
No but for real, if you don't I will slap you so hard your grandkids will get a hand mark on their face
