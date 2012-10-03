"""
    @package    soup-can
    @file       soupparser.py
    @author     Daniel Rahier <daniel@rahier.biz>

    Parser for html pages as found on soup.io
    Python 2 implementation.
"""

from HTMLParser import HTMLParser


class Post(object):
    """Represents meta data of a single post to soup.io"""
    def __init__(self, pid, ptype):
        self.pid = pid
        self.ptype = ptype ## type of post, e.g. Image, Text, etc.
        self.title = ''
        self.source = '' ## url to original, if not specified url to soup post
        self.text = '' ## content of text post
        self.url = '' ## url of image for image posts

    def __unicode__(self):
        return self.pid


class LastPostMatch(Exception):
    """SoupParser found matching post so it can end parsing further tags."""
    pass


class SoupParser(HTMLParser):

    def __init__(self, html, last_post_id):
        """Parses given html string and retrieves posts up to last_post_id.
        @param html         (unicode) string that represents a single page from
                            a soup.
        @param last_post_id html will be parsed until a post with this id is
                            found.
        """
        HTMLParser.__init__(self)
        self.embed_tags = list()
        self.image_post = False
        self.inside_embed = -1
        self.inside_post = False
        self.last_post_id = None
        self.tag_stack = list()
        self.text_post = False
        self.posts = list()
        self.video_post = False

        self.last_post_id = last_post_id
        self.feed(html) ## start html parsing

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tag_stack.append((tag.lower(), attrs))

        if self.inside_post:
            self.process_common_data(tag, attrs)
        if self.image_post:
            self.process_image_post(tag, attrs)
        elif self.text_post:
            self.process_text_post(tag, attrs)
        elif self.video_post:
            self.process_video_post(tag, attrs)
        elif tag == 'div' and len(self.tag_stack) == 11:
            new_post = False
            if any('post_image' in v for v in attrs.values()):
                #post_id = attrs['id'].split('post')[1]
                #self.posts.append(Post(pid=post_id, ptype='image'))
                new_post = self.image_post = self.inside_post = True
                ptype = 'image'
            elif any('post_regular' in v for v in attrs.values()):
                # Skip reactions for now:
                if 'post_reaction' not in attrs['class']:
                    #post_id = attrs['id'].split('post')[1]
                    #self.posts.append(Post(pid=post_id, ptype='text'))
                    new_post = self.text_post = self.inside_post = True
                    ptype = 'text'
            elif any('post_video' in v for v in attrs.values()):
                #post_id = attrs['id'].split('post')[1]
                #self.posts.append(Post(pid=post_id, ptype='video'))
                new_post = self.video_post = self.inside_post = True
                ptype = 'video'
            if new_post:
                post_id = attrs['id'].split('post')[1]
                if post_id == self.last_post_id:
                    raise LastPostMatch("Found last post")
                else:
                    self.posts.append(Post(pid=post_id, ptype=ptype))


    def handle_endtag(self, tag):
        self.tag_stack.pop()

        if len(self.tag_stack) == 10 and self.inside_post:
            self.image_post = self.text_post = self.inside_post = False
            self.video_post = False

        ## video embed code is a bit tricky because we need to store all
        ## html tags and their attributes
        elif self.inside_embed - 2 == len(self.tag_stack): ## end of embed
            self.inside_embed = -1

            ## create html from stored tag list
            embed_code = ''
            for (tag, attrs) in self.embed_tags:
                if attrs == 'endtag':
                    embed_code += '</%s>' % tag
                else:
                    a = ''
                    for k, v in attrs.iteritems():
                        a = '%s %s="%s"' % (a, k, v)
                    embed_code = "%s<%s%s>" % (embed_code, tag, a)
            
            self.posts[-1].source = embed_code
            self.embed_tags = list()
        elif self.inside_embed != -1: ## still inside embed tag for video
            ## this is a closing tag, so mark it accordingly
            self.embed_tags.append((tag, 'endtag'))

    def process_common_data(self, tag, attrs):
        # search for a tag containing the title of the post
        if 'icon type' in self.tag_stack[-2][1].values():
            # add title to last post
            self.posts[-1].title = unicode(attrs['title'])
        # set source of post to that of original soup poster
        elif 'url avatarlink' in self.tag_stack[-1][1].values():
            # don't replace original with "via user"
            if len(self.posts[-1].source) == 0:
                self.posts[-1].source = attrs['href']

    def process_image_post(self, tag, attrs):
        # check for imagecontainer div
        if 'imagecontainer' in self.tag_stack[-2][1].values():
            # image urls might be stored inside an <a> or <img> tag, depending
            # on their size (special handling for images with width > 600px).
            if tag == 'a':
                self.posts[-1].url = attrs['href']
            elif tag == 'img':
                self.posts[-1].url = attrs['src']

        # check for original source of image which is stored in its caption
        elif 'caption' in self.tag_stack[-2][1].values():
            try:
                self.posts[-1].source = attrs['href']
            except KeyError:
               pass

    def process_text_post(self, tag, attrs):
        pass ## nothing special to do for now


    def process_video_post(self, tag, attrs):
        if len(self.embed_tags) > 0:
            self.embed_tags.append((tag, attrs))

        ## Make sure we do this only once as there could be further embed tags
        ## inside embed. Especially youtube does this.
        elif 'embed' in self.tag_stack[-2][1].values():
            ## safe stack depth so we know when embed ends
            self.inside_embed = len(self.tag_stack)
            self.embed_tags.append((tag, attrs))
