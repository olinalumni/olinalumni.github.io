<card-list>
    <div each={{opts.cards}} class="card row">
        <div>
            <h4 if={links.title}><a href="{links.title}">{{title}} <small if={subtitle}>{{subtitle}}</small></a></h4>
            <h4 if={!links.title}>{{title}} <small if={subtitle}>{{subtitle}}</small></h4>
            <p if={description}>{{description}}</p>
            <div>
                <ul class= "links list-unstyled">
                    <li if={links.www}><a class="btn btn-xs btn-default" href="{links.www}"><i class="fa fa-link"></i> website</a></li>
                    <li if={links.email}><a class="btn btn-xs btn-default" href="{links.email}"><i class="fa fa-envelope-o"></i> email</a></li>
                    <li if={links.youtube}><a class="btn btn-xs btn-default" href="{links.youtube}"><i class="fa fa-youtube-play"></i> youtube</a></li>
                    <li if={links.instagram}><a class="btn btn-xs btn-default" href="https://instagram.com/{links.instagram}"><i class="fa fa-instagram"></i> instagram</a></li>
                    <li if={links.github}><a class="btn btn-xs btn-default" href="https://github.com/{links.github}"><i class="fa fa-github"></i> github</a></li>
                    <li if={links.facebook}><a class="btn btn-xs btn-default" href="https://facebook.com/{links.facebook}"><i class="fa fa-facebook"></i> facebook</a></li>
                    <li if={links.twitter}><a class="btn btn-xs btn-default" href="https://twitter.com/{links.twitter}"><i class="fa fa-twitter"></i> twitter</a></li>
                </ul>
            </div>
            <div if={links.facebook} class="fb-page"
                data-href="https://www.facebook.com/{links.facebook}/"
                data-small-header="true"
                data-adapt-container-width="true"
                data-hide-cover="false"
                data-show-facepile="false">
                <blockquote cite="https://www.facebook.com/{links.facebook}/" class="fb-xfbml-parse-ignore">
                    <a href="https://www.facebook.com/{links.facebook}/">{title}</a>
                </blockquote>
            </div>
            <div if={links.twitter}>
                <p style="margin: 0.5em 0"><a class="twitter-follow-button"
                    href="https://twitter.com/{links.twitter}"
                    data-size="large">
                    Follow @{links.twitter}
                </a></p>
            </div>
        </div>
    </div>
</card-list>