<card-list>
    <div each={{opts.cards}} class="card row col-xs-5">
        <div class="info">
            <h3>{{mainHeading}} <small>{{subHeading}}</small></h3>
            <p id="description">
                {{description}}
            </p>
            
            <div class="contact">
              <ul class= "links list-unstyled">
                <li if={socialMedia.webURL}> <a href={socialMedia.webURL}><i class="fa fa-link"></i></a> </li>
                <li if={socialMedia.emailURL}> <a href={socialMedia.emailURL}><i class="fa fa-envelope-o"></i></a> </li>
                <li if={socialMedia.facebookURL}> <a href={socialMedia.facebookURL}><i class="fa fa-facebook"></i></a> </li>
                <li if={socialMedia.twitterURL}> <a href={socialMedia.twitterURL}v><i class="fa fa-twitter"></i></a> </li>
              </ul>
            </div>
        </div>
    </div>
</card-list>